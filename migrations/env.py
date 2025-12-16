"""
Alembic environment configuration.

This file tells Alembic:
1. Where to find our models (for autogenerate)
2. How to connect to database (from .env)
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import our config and Base
from src.fastapi_auth.core.config import settings
from src.fastapi_auth.models.base import Base

# Import model MODULES (not classes) to register them with SQLAlchemy
# This avoids the "table already defined" error
# Import the module itself, which will trigger the class definition
from src.fastapi_auth.models import user  # noqa: F401 - Import module, not User class

# this is the Alembic Config object
config = context.config

# Set the database URL from our .env settings
# Convert async URL to sync for Alembic (it doesn't support async)
database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata so Alembic knows about our models
# This enables autogenerate (automatic migration creation)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without executing)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (executes against database)."""
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
