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
"""

from typing import Dict, List, Optional

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.database.database import Database, DatabaseError, get_database
from app.database.models import ALL_MODELS, Base
from app.logger import logger


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

    Verifies connectivity, then creates any missing tables. Intended to
    be called once at application startup.

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
