"""Alembic environment configuration for ExamLens AI.

Reads DATABASE_URL from the environment (or falls back to alembic.ini)
and uses ``Base.metadata`` from ``src.models`` for autogenerate support.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config object – provides access to values in alembic.ini
config = context.config

# Set up Python logging from the ini file (if present).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Override sqlalchemy.url from DATABASE_URL env var when available.
# This lets CI / Docker pass the URL without editing alembic.ini.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Import all models so Alembic can discover them for autogenerate.
from src.models import Base  # noqa: E402  (import after sys.path is set)

target_metadata = Base.metadata


# Migration runners
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without a live DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to a live DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
