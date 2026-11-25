"""Alembic environment. The URL comes from the caller (lmx.db.migrate / tests), never from a config file."""

from alembic import context
from sqlalchemy import engine_from_config, pool

import lmx.models  # noqa: F401  # pyright: ignore[reportUnusedImport]  (registers the tables)
from lmx.db import Base

config = context.config
target_metadata = Base.metadata


def run() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {}, prefix='sqlalchemy.', poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


run()
