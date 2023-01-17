import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine


sys.path.append(os.path.join(os.path.dirname(__file__),'../'))
from lionbot.data import Base

config = context.config
fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
    if database_uri and database_uri.startswith("postgres://"):
        database_uri = database_uri.replace("postgres://", "postgresql://", 1)
    context.configure(
        url=database_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
    if database_uri and database_uri.startswith("postgres://"):
        database_uri = database_uri.replace("postgres://", "postgresql://", 1)
    connectable = create_engine(database_uri)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
