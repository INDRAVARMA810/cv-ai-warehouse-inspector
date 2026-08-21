"""Schema initialization and inspection.

Creates, drops and inspects the tables defined in
:mod:`app.database.models`.

**This is schema initialization, not a migration framework.**
``create_all`` only creates tables that do not yet exist — it will not
alter an existing table when a model changes. That is fine for first
deployment and for development, but a production system whose schema
evolves needs versioned, reversible migrations. Alembic is the standard
choice for SQLAlchemy and is not currently a project dependency; see
:func:`migration_guidance`.

One narrow exception: :func:`upgrade_track_run_id_column` performs a
single, additive, idempotent upgrade for a known schema gap (see the
docstring on ``app.database.models.TrackRecord.run_id``) so that a
database created before ``run_id`` existed does not start failing every
track write the moment this code ships. It is deliberately not a
general-purpose migration mechanism — see its docstring for exactly
what it will and will not do.
"""

from typing import Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.database import Database, DatabaseError, get_database
from app.database.models import ALL_MODELS, Base
from app.logger import logger

#: Value stamped onto pre-existing ``track_records`` rows that predate
#: the ``run_id`` column, so they remain queryable and are visibly
#: distinct from any real pipeline run's UUID.
LEGACY_RUN_ID = "legacy-pre-run-id"


def create_schema(database: Optional[Database] = None) -> bool:
    """Create every table that does not already exist.

    Existing tables are left untouched, including when their definition
    has drifted from the model.

    Args:
        database: The database to operate on. Defaults to the
            process-wide instance.

    Returns:
        ``True`` on success, ``False`` if the operation failed.
    """
    target = database or get_database()

    try:
        Base.metadata.create_all(bind=target.engine)
    except (SQLAlchemyError, DatabaseError) as exc:
        logger.error(f"Schema creation failed: {exc}")
        return False

    logger.info(
        f"Schema ready on {target.config.safe_url()}: "
        f"{', '.join(model.__tablename__ for model in ALL_MODELS)}"
    )
    return True


def upgrade_track_run_id_column(database: Optional[Database] = None) -> bool:
    """Add ``track_records.run_id`` to a database created before it existed.

    ``create_schema()`` cannot do this — ``create_all()`` only creates
    missing tables, never alters an existing one — so a database that
    already has a ``track_records`` table from before ``run_id`` was
    introduced would otherwise fail on the very first track write after
    an upgrade, with no warning at startup.

    This performs exactly one thing, additively and idempotently:

    1. If ``track_records`` does not exist yet, do nothing —
       :func:`create_schema` will create it correctly, ``run_id``
       included, from the current model.
    2. If it exists and already has ``run_id``, do nothing except retry
       adding the unique constraint if a previous run of this function
       left it missing (see step 4).
    3. Otherwise: add the column (nullable), backfill every existing
       row with :data:`LEGACY_RUN_ID`, then set it ``NOT NULL``. This
       step never deletes or overwrites any existing data — it only
       adds a column and fills in a value that did not exist before.
    4. Attempt to add ``UNIQUE(run_id, track_id)``. Because every
       legacy row shares the same backfilled ``run_id``, this succeeds
       unless two legacy rows already share a ``track_id`` — which
       would mean the exact corruption this whole fix targets already
       happened before the fix was applied. In that case the failure
       is logged clearly and startup continues without the constraint;
       the column and backfill are already committed, so a manual
       dedup followed by a restart will complete the upgrade.

    Only acts on PostgreSQL. SQLite databases in this project are
    always freshly created via :func:`create_schema` (there is no
    supported path where a pre-``run_id`` SQLite file needs upgrading),
    and SQLite's limited ``ALTER TABLE`` support makes the same
    additive approach unreliable there — so this is a deliberate no-op
    on every other dialect, not an oversight.

    Args:
        database: The database to operate on. Defaults to the
            process-wide instance.

    Returns:
        ``True`` if the database is left in a usable state (which
        includes "nothing needed to change" and "upgraded but the
        unique constraint could not yet be added"). ``False`` only if
        the required column-and-backfill step itself failed.
    """
    target = database or get_database()

    if target.engine.dialect.name != "postgresql":
        logger.debug(
            f"Skipping track_records.run_id upgrade check on "
            f"'{target.engine.dialect.name}' dialect (PostgreSQL only)."
        )
        return True

    inspector = inspect(target.engine)

    if "track_records" not in inspector.get_table_names():
        return True

    existing_columns = {col["name"] for col in inspector.get_columns("track_records")}
    constraint_name = "uq_track_records_run_id_track_id"

    if "run_id" not in existing_columns:
        logger.warning(
            "track_records predates the run_id column; applying an additive "
            "upgrade (add column, backfill existing rows as "
            f"'{LEGACY_RUN_ID}', set NOT NULL). No existing data will be "
            "deleted or overwritten."
        )
        try:
            with target.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE track_records ADD COLUMN run_id VARCHAR(36)")
                )
                result = connection.execute(
                    text(
                        "UPDATE track_records SET run_id = :legacy "
                        "WHERE run_id IS NULL"
                    ),
                    {"legacy": LEGACY_RUN_ID},
                )
                connection.execute(
                    text("ALTER TABLE track_records ALTER COLUMN run_id SET NOT NULL")
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_track_records_run_id "
                        "ON track_records (run_id)"
                    )
                )
        except SQLAlchemyError as exc:
            logger.error(f"track_records.run_id upgrade failed: {exc}")
            return False

        logger.info(
            f"track_records.run_id added; backfilled {result.rowcount} "
            f"existing row(s) as '{LEGACY_RUN_ID}'."
        )
    else:
        existing_unique = {
            uc["name"] for uc in inspector.get_unique_constraints("track_records")
        }
        if constraint_name in existing_unique:
            return True

    # Reaching here means the constraint is missing — either just-added
    # rows need it for the first time, or a previous attempt below
    # failed and this is a retry. Run in its own transaction, separate
    # from the block above, so a failure here cannot roll back a
    # column-and-backfill that already succeeded.
    try:
        with target.engine.begin() as connection:
            connection.execute(
                text(
                    f"ALTER TABLE track_records ADD CONSTRAINT {constraint_name} "
                    "UNIQUE (run_id, track_id)"
                )
            )
        logger.info(f"Added unique constraint {constraint_name} on track_records.")
    except SQLAlchemyError as exc:
        logger.warning(
            f"Could not add unique constraint {constraint_name} on "
            f"track_records — likely a pre-existing duplicate (run_id, "
            f"track_id) pair from before this fix. track_records.run_id "
            f"is in place and new writes are correctly scoped; existing "
            f"duplicates need manual review before the constraint can be "
            f"added. Original error: {exc}"
        )

    return True


def drop_schema(database: Optional[Database] = None, confirm: bool = False) -> bool:
    """Drop every table defined by the models.

    Args:
        database: The database to operate on. Defaults to the
            process-wide instance.
        confirm: Must be ``True`` for the drop to proceed. This guard
            exists because the operation destroys all stored alerts and
            audit history irreversibly.

    Returns:
        ``True`` if the schema was dropped, ``False`` otherwise.
    """
    if not confirm:
        logger.error(
            "drop_schema() refused: pass confirm=True to acknowledge that "
            "this permanently destroys all stored data."
        )
        return False

    target = database or get_database()

    try:
        Base.metadata.drop_all(bind=target.engine)
    except (SQLAlchemyError, DatabaseError) as exc:
        logger.error(f"Schema drop failed: {exc}")
        return False

    logger.warning(f"Schema dropped on {target.config.safe_url()}.")
    return True


def reset_schema(database: Optional[Database] = None, confirm: bool = False) -> bool:
    """Drop and recreate the schema.

    Args:
        database: The database to operate on.
        confirm: Must be ``True``; see :func:`drop_schema`.

    Returns:
        ``True`` if the schema was reset, ``False`` otherwise.
    """
    if not drop_schema(database=database, confirm=confirm):
        return False

    return create_schema(database=database)


def list_tables(database: Optional[Database] = None) -> List[str]:
    """Return the table names present in the database.

    Args:
        database: The database to inspect.

    Returns:
        The existing table names, or an empty list if inspection fails.
    """
    target = database or get_database()

    try:
        return list(inspect(target.engine).get_table_names())
    except (SQLAlchemyError, DatabaseError) as exc:
        logger.error(f"Could not list tables: {exc}")
        return []


def verify_schema(database: Optional[Database] = None) -> Dict[str, bool]:
    """Check which expected tables exist.

    Args:
        database: The database to inspect.

    Returns:
        A ``{table_name: exists}`` mapping covering every model.
    """
    existing = set(list_tables(database=database))
    status = {model.__tablename__: model.__tablename__ in existing for model in ALL_MODELS}

    missing = [name for name, present in status.items() if not present]
    if missing:
        logger.warning(f"Missing table(s): {', '.join(missing)}")

    return status


def schema_is_ready(database: Optional[Database] = None) -> bool:
    """Return whether every expected table exists.

    Args:
        database: The database to inspect.

    Returns:
        ``True`` if all model tables are present.
    """
    return all(verify_schema(database=database).values())


def initialize(database: Optional[Database] = None) -> bool:
    """Prepare the database for use.

    Verifies connectivity, creates any missing tables, then applies the
    one narrow additive upgrade this module knows about (see
    :func:`upgrade_track_run_id_column`). Intended to be called once at
    application startup.

    Args:
        database: The database to initialize.

    Returns:
        ``True`` if the database is reachable and the schema is ready.
    """
    target = database or get_database()

    if not target.check_connection():
        logger.error(
            f"Cannot initialize schema: {target.config.safe_url()} is unreachable."
        )
        return False

    if not create_schema(database=target):
        return False

    if not upgrade_track_run_id_column(database=target):
        return False

    return schema_is_ready(database=target)


def migration_guidance() -> str:
    """Return guidance on moving to versioned migrations.

    Returns:
        A short explanation of this module's limits and the recommended
        production approach.
    """
    return (
        "app.database.migrations performs schema *initialization* only: "
        "create_all() adds missing tables but never alters existing ones, "
        "so a model change will not reach a database that already has the "
        "old table. Before the schema evolves in production, adopt Alembic "
        "(`pip install alembic`, `alembic init migrations`), point its "
        "target_metadata at app.database.models.Base.metadata, and manage "
        "changes as versioned, reversible revisions."
    )
