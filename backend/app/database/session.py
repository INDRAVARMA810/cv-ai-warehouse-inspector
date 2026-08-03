"""Session construction and transaction scoping.

Provides the unit-of-work boundary for the persistence layer. Callers
obtain a session from :func:`session_scope`, which commits on success
and rolls back on any exception — so a partially-applied write can
never be left behind by a failure mid-way through a batch.

Sessions are created lazily from the engine in :mod:`app.database.database`,
so importing this module does not connect to anything.
"""

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.database.database import Database, get_database
from app.logger import logger


class SessionManager:
    """Builds and scopes sessions for a single :class:`Database`.

    Attributes:
        database: The database sessions are opened against.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        """Configure the manager without connecting.

        Args:
            database: The database to bind to. Defaults to the
                process-wide instance.
        """
        self._database = database
        self._factory: Optional[sessionmaker] = None
        self._scoped: Optional[scoped_session] = None

    @property
    def database(self) -> Database:
        """Return the bound database, resolving the default if needed."""
        if self._database is None:
            self._database = get_database()
        return self._database

    @property
    def factory(self) -> sessionmaker:
        """Return the session factory, creating it on first access."""
        if self._factory is None:
            self._factory = sessionmaker(
                bind=self.database.engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            logger.debug("Session factory created.")
        return self._factory

    @property
    def scoped(self) -> scoped_session:
        """Return a thread-local scoped session registry.

        Each thread that touches this receives its own session, which
        matters for a pipeline that may persist from a worker thread
        while the main thread reads.

        Returns:
            The scoped session registry.
        """
        if self._scoped is None:
            self._scoped = scoped_session(self.factory)
            logger.debug("Scoped session registry created.")
        return self._scoped

    def create_session(self) -> Session:
        """Create a new, unmanaged session.

        The caller becomes responsible for committing, rolling back and
        closing it. Prefer :meth:`session_scope` unless that control is
        genuinely needed.

        Returns:
            A new :class:`~sqlalchemy.orm.Session`.
        """
        return self.factory()

    @contextmanager
    def session_scope(self, commit: bool = True) -> Iterator[Session]:
        """Provide a transactional session scope.

        Commits on clean exit, rolls back on any exception, and always
        closes the session::

            with manager.session_scope() as session:
                AlertRepository(session).create(...)

        Args:
            commit: Whether to commit on success. Pass ``False`` for
                read-only work to avoid a pointless round trip.

        Yields:
            The session for the duration of the block.

        Raises:
            Exception: Re-raises whatever the caller's block raised,
                after rolling back.
        """
        session = self.create_session()

        try:
            yield session
            if commit:
                session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.error(f"Database transaction rolled back: {exc}")
            raise
        except Exception:
            session.rollback()
            logger.exception("Transaction rolled back due to an unexpected error.")
            raise
        finally:
            session.close()

    def remove_scoped_session(self) -> None:
        """Dispose of the current thread's scoped session.

        Call at the end of a request or worker iteration so the session
        does not outlive its unit of work.
        """
        if self._scoped is not None:
            self._scoped.remove()

    def dispose(self) -> None:
        """Discard the factory, registry and underlying engine."""
        self.remove_scoped_session()
        self._factory = None
        self._scoped = None

        if self._database is not None:
            self._database.dispose()


#: Process-wide session manager, created lazily.
_default_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Return the process-wide :class:`SessionManager`.

    Returns:
        The shared manager, created on first call.
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = SessionManager()

    return _default_manager


def set_session_manager(manager: Optional[SessionManager]) -> None:
    """Replace the process-wide session manager.

    Intended for tests and for binding the application to a specific
    database at startup.

    Args:
        manager: The manager to install, or ``None`` to clear it.
    """
    global _default_manager
    _default_manager = manager


@contextmanager
def session_scope(commit: bool = True) -> Iterator[Session]:
    """Provide a transactional scope from the default session manager.

    Args:
        commit: Whether to commit on success.

    Yields:
        A session bound to the process-wide database.
    """
    with get_session_manager().session_scope(commit=commit) as session:
        yield session


def get_session() -> Session:
    """Create an unmanaged session from the default manager.

    The caller owns its lifecycle. Prefer :func:`session_scope`.

    Returns:
        A new session.
    """
    return get_session_manager().create_session()
