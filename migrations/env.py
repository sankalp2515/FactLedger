"""Migration environment. Credentials come from Settings and are never logged."""

from alembic import context
from product_core import models  # noqa: F401
from product_core.config import Settings
from product_core.db import Base
from sqlalchemy import create_engine, pool

target_metadata = Base.metadata


def run_migrations():
    url = Settings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


run_migrations()
