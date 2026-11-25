"""Schema changes only through migrations, and migrations must match the models exactly."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from lmx.db import MIGRATIONS, Base, migrate


def config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option('script_location', str(MIGRATIONS))
    cfg.set_main_option('sqlalchemy.url', url)
    return cfg


def test_models_match_migrations(tmp_path: Path) -> None:
    """If this fails you changed a model without writing a migration (or the other way round)."""
    url = f'sqlite:///{tmp_path / "db.sqlite"}'
    migrate(url)
    with create_engine(url).connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={'compare_type': True}), Base.metadata)
    assert diff == []


def test_single_head_and_linear_history() -> None:
    scripts = ScriptDirectory.from_config(config('sqlite://'))
    assert len(scripts.get_heads()) == 1, 'multiple migration heads: merge them'


def test_down_and_up_again(tmp_path: Path) -> None:
    url = f'sqlite:///{tmp_path / "db.sqlite"}'
    migrate(url)
    command.downgrade(config(url), 'base')
    assert set(inspect(create_engine(url)).get_table_names()) <= {'alembic_version'}
    migrate(url)
    assert {'users', 'knowledge_events', 'word_knowledge'} <= set(inspect(create_engine(url)).get_table_names())


def test_migrate_is_idempotent_and_keeps_data(tmp_path: Path) -> None:
    url = f'sqlite:///{tmp_path / "db.sqlite"}'
    migrate(url)
    with create_engine(url).begin() as conn:
        conn.execute(text("INSERT INTO users (name, created_at) VALUES ('me', '2026-01-01')"))
    migrate(url)
    with create_engine(url).connect() as conn:
        assert conn.execute(text('SELECT name FROM users')).scalars().all() == ['me']
