from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Load settings to obtain the Postgres DSN. This import was missing, causing a NameError
# during alembic execution in the container startup.
from common.config.settings import load_settings

# Alembic Config object provides access to configuration values.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# We do not use SQLAlchemy models; migrations are fully imperative.
target_metadata = None


def _get_database_url() -> str:
    # Use centralized configuration for the Postgres DSN.
    _settings = load_settings()
    env_url = _settings.postgres_url
    if env_url:
        return env_url
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = engine_from_config(
        configuration,
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
