"""Database engine + session. Schema changes only through Alembic migrations (see migrations/)."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

MIGRATIONS = Path(__file__).resolve().parent / 'migrations'


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    # SQLite: shared across threads (sessions are per request/job); wait up to 30 s for another writer
    sqlite_args = {'check_same_thread': False, 'timeout': 30}
    engine = create_engine(url, connect_args=sqlite_args if url.startswith('sqlite') else {})
    if url.startswith('sqlite'):

        @event.listens_for(engine, 'connect')
        def _pragmas(conn, _record):  # type: ignore[no-untyped-def]
            cur = conn.cursor()
            cur.execute('PRAGMA foreign_keys=ON')
            cur.execute('PRAGMA journal_mode=WAL')
            cur.close()

    return engine


def migrate(url: str, revision: str = 'head') -> None:
    """Bring the database to `revision` (used at startup and by the tests)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option('script_location', str(MIGRATIONS))
    cfg.set_main_option('sqlalchemy.url', url)
    command.upgrade(cfg, revision)


class Database:
    def __init__(self, url: str):
        self.url = url
        self.engine = make_engine(url)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Generator[Session]:
        """One unit of work: commit on success, roll back on error."""
        s = self._sessions()
        try:
            yield s
            s.commit()
        except BaseException:
            s.rollback()
            raise
        finally:
            s.close()
