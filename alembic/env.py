"""Alembic migration environment.

Wires Alembic to the application's ORM metadata and database URL so that
autogenerate and `upgrade`/`downgrade` operate on the same schema the app
uses. The URL always comes from `settings.database_url`, never from
`alembic.ini`, keeping a single source of truth.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.adapters.persistence.orm import Base
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DBAPI connection, emitting SQL."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection built from the app settings."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
