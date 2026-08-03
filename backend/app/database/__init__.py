"""Persistence layer.

Stores alerts, the violations behind them, tracked-object lifetimes and
system events in PostgreSQL.

The layer is arranged so that no business logic ever writes a query:

* :mod:`app.database.database` owns the engine and connection pool.
* :mod:`app.database.session` owns transaction scoping.
* :mod:`app.database.models` defines the schema.
* :mod:`app.database.repositories` is the **only** place that reads or
  writes data. Everything above this layer calls repositories.
* :mod:`app.database.migrations` initializes the schema.
* :mod:`app.database.seed` inserts demo data.

Importing this package never opens a connection — the engine is built
on first use — so the rest of the application remains importable and
testable without a running database.
"""

from app.database.database import (
    Database,
    DatabaseConfig,
    DatabaseError,
    get_database,
    normalize_database_url,
    set_database,
)
from app.database.migrations import (
    create_schema,
    drop_schema,
    initialize,
    list_tables,
    migration_guidance,
    reset_schema,
    schema_is_ready,
    verify_schema,
)
from app.database.models import (
    ALL_MODELS,
    AlertRecord,
    Base,
    SystemEvent,
    TrackRecord,
    ViolationRecord,
    datetime_to_epoch,
    epoch_to_datetime,
    utcnow,
)
from app.database.repositories import (
    AlertRepository,
    BaseRepository,
    Page,
    RepositoryBundle,
    SystemRepository,
    TrackRepository,
    ViolationRepository,
)
from app.database.seed import SeedResult, seed, seed_session
from app.database.session import (
    SessionManager,
    get_session,
    get_session_manager,
    session_scope,
    set_session_manager,
)

__all__ = [
    # Engine & configuration
    "Database",
    "DatabaseConfig",
    "DatabaseError",
    "get_database",
    "set_database",
    "normalize_database_url",
    # Sessions
    "SessionManager",
    "session_scope",
    "get_session",
    "get_session_manager",
    "set_session_manager",
    # Models
    "Base",
    "AlertRecord",
    "ViolationRecord",
    "TrackRecord",
    "SystemEvent",
    "ALL_MODELS",
    "utcnow",
    "epoch_to_datetime",
    "datetime_to_epoch",
    # Repositories
    "BaseRepository",
    "AlertRepository",
    "ViolationRepository",
    "TrackRepository",
    "SystemRepository",
    "RepositoryBundle",
    "Page",
    # Schema
    "initialize",
    "create_schema",
    "drop_schema",
    "reset_schema",
    "list_tables",
    "verify_schema",
    "schema_is_ready",
    "migration_guidance",
    # Seeding
    "seed",
    "seed_session",
    "SeedResult",
]
