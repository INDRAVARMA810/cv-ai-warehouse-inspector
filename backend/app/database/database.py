"""Database engine construction and connection configuration.

Owns the SQLAlchemy :class:`~sqlalchemy.engine.Engine` and its
connection pool. Configuration is read from environment variables,
falling back to :mod:`app.config` for the connection URL.

The engine is created **lazily**. Importing this module — or anything
in :mod:`app.database` — must never open a socket, so the rest of the
application can be imported and unit-tested without a running database.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool, QueuePool

from app.config import settings
from app.logger import logger


class DatabaseError(Exception):
    """Raised when the database cannot be configured or reached."""


def _env_int(name: str, default: int) -> int:
    """Read a non-negative integer from the environment.

    Args:
        name: Environment variable name.
        default: Value to use when unset or malformed.

    Returns:
        The parsed value, or ``default`` if unset or invalid.
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        return int(raw)
    except ValueError:
        logger.warning(
            f"Environment variable {name}={raw!r} is not an integer; "
            f"using default {default}."
        )
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean from the environment.

    Args:
        name: Environment variable name.
        default: Value to use when unset.

    Returns:
        ``True`` for "1", "true", "yes" or "on" (case-insensitive).
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(url: str) -> str:
    """Ensure a PostgreSQL URL names an installed driver.

    A bare ``postgresql://`` URL resolves to the ``psycopg2`` dialect,
    but this project installs **psycopg 3**. Left alone, the engine
    would fail at connect time with a confusing ``ModuleNotFoundError``.
    This rewrites the scheme to ``postgresql+psycopg://`` so the
    configured URL works as written.

    Args:
        url: The configured connection URL.

    Returns:
        The URL with an explicit driver, unchanged if one is already
        given or the backend is not PostgreSQL.

    Raises:
        DatabaseError: If the URL cannot be parsed.
    """
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise DatabaseError(f"Invalid database URL: {exc}") from exc

    if parsed.get_backend_name() != "postgresql":
        return url

    if "+" in parsed.drivername:
        return url

    normalized = parsed.set(drivername="postgresql+psycopg")
    logger.debug(
        "Rewrote bare 'postgresql://' URL to 'postgresql+psycopg://' "
        "(psycopg 3 is the installed driver)."
    )
    return normalized.render_as_string(hide_password=False)


@dataclass
class DatabaseConfig:
    """Connection and pooling settings.

    Attributes:
        url: SQLAlchemy connection URL.
        pool_size: Connections kept open in the pool.
        max_overflow: Extra connections allowed beyond ``pool_size``
            during bursts.
        pool_timeout: Seconds to wait for a free connection before
            failing.
        pool_recycle: Seconds after which a connection is recycled.
            Guards against servers and proxies silently dropping idle
            connections.
        pool_pre_ping: Whether to validate a connection before handing
            it out. Costs one round trip but avoids handing callers a
            stale socket.
        echo: Whether SQLAlchemy should log every statement.
        use_pooling: Whether to pool at all. SQLite in-memory databases
            must not pool, since each new connection would see a
            different empty database.
    """

    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    echo: bool = False
    use_pooling: bool = True

    @classmethod
    def from_env(cls, url: Optional[str] = None) -> "DatabaseConfig":
        """Build configuration from environment variables.

        Reads ``DATABASE_URL``, ``DB_POOL_SIZE``, ``DB_MAX_OVERFLOW``,
        ``DB_POOL_TIMEOUT``, ``DB_POOL_RECYCLE``, ``DB_POOL_PRE_PING``
        and ``DB_ECHO``. The connection URL falls back to
        ``settings.database_url``.

        Args:
            url: Explicit URL, overriding both the environment and
                application settings.

        Returns:
            The resulting configuration.
        """
        resolved = url or os.getenv("DATABASE_URL") or settings.database_url
        resolved = normalize_database_url(resolved)

        is_memory_sqlite = resolved.startswith("sqlite") and ":memory:" in resolved

        return cls(
            url=resolved,
            pool_size=_env_int("DB_POOL_SIZE", 5),
            max_overflow=_env_int("DB_MAX_OVERFLOW", 10),
            pool_timeout=_env_int("DB_POOL_TIMEOUT", 30),
            pool_recycle=_env_int("DB_POOL_RECYCLE", 1800),
            pool_pre_ping=_env_bool("DB_POOL_PRE_PING", True),
            echo=_env_bool("DB_ECHO", False),
            use_pooling=not is_memory_sqlite,
        )

    def engine_kwargs(self) -> Dict[str, Any]:
        """Build the keyword arguments for :func:`sqlalchemy.create_engine`.

        Returns:
            Engine options appropriate to the configured backend. Pool
            sizing options are omitted for backends that cannot use
            them.
        """
        kwargs: Dict[str, Any] = {
            "echo": self.echo,
            "future": True,
            "pool_pre_ping": self.pool_pre_ping,
        }

        if not self.use_pooling:
            kwargs["poolclass"] = NullPool
            # NullPool holds no connections, so sizing and pre-ping
            # options do not apply.
            kwargs.pop("pool_pre_ping", None)
            return kwargs

        if self.url.startswith("sqlite"):
            # File-backed SQLite pools, but not with QueuePool sizing.
            return kwargs

        kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
            }
        )
        return kwargs

    def safe_url(self) -> str:
        """Return the URL with the password masked, for logging.

        Returns:
            The connection URL, safe to write to logs.
        """
        try:
            return make_url(self.url).render_as_string(hide_password=True)
        except Exception:
            return "<unparseable url>"


class Database:
    """Owns a SQLAlchemy engine and its lifecycle.

    The engine is built on first use rather than at construction, so a
    :class:`Database` can be created in module scope without requiring
    a reachable server.

    Attributes:
        config: The connection and pooling settings in effect.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """Configure the database without connecting.

        Args:
            config: Connection settings. Defaults to
                :meth:`DatabaseConfig.from_env`.
        """
        self.config = config or DatabaseConfig.from_env()
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        """Return the engine, creating it on first access.

        Returns:
            The configured :class:`~sqlalchemy.engine.Engine`.

        Raises:
            DatabaseError: If the engine cannot be created.
        """
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        """Build the SQLAlchemy engine.

        Returns:
            The new engine.

        Raises:
            DatabaseError: If engine creation fails.
        """
        try:
            engine = create_engine(self.config.url, **self.config.engine_kwargs())
        except Exception as exc:
            raise DatabaseError(
                f"Failed to create engine for {self.config.safe_url()}: {exc}"
            ) from exc

        logger.info(
            f"Database engine created for {self.config.safe_url()} "
            f"(driver={engine.dialect.driver}, "
            f"pooling={'on' if self.config.use_pooling else 'off'})"
        )
        return engine

    def check_connection(self) -> bool:
        """Test whether the database is reachable.

        Returns:
            ``True`` if a trivial statement succeeds, ``False``
            otherwise. Never raises, so callers can use it as a health
            probe.
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except (SQLAlchemyError, DatabaseError) as exc:
            logger.error(f"Database connection check failed: {exc}")
            return False

        logger.debug("Database connection check succeeded.")
        return True

    def dispose(self) -> None:
        """Close all pooled connections and discard the engine.

        Safe to call when no engine was ever created.
        """
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            logger.info("Database engine disposed; pooled connections closed.")


#: Process-wide default database. Created eagerly but connects lazily,
#: so importing this module remains side-effect free.
_default_database: Optional[Database] = None


def get_database() -> Database:
    """Return the process-wide :class:`Database` instance.

    Returns:
        The shared database, created on first call.
    """
    global _default_database

    if _default_database is None:
        _default_database = Database()

    return _default_database


def set_database(database: Optional[Database]) -> None:
    """Replace the process-wide database.

    Intended for tests and for pointing the application at an
    alternative backend at startup.

    Args:
        database: The database to install, or ``None`` to clear it so
            the next :func:`get_database` call rebuilds from the
            environment.
    """
    global _default_database

    if _default_database is not None and _default_database is not database:
        _default_database.dispose()

    _default_database = database
