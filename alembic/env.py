import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure project root is on sys.path so package imports work (vpn_api)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging

from vpn_api import models

# Import application metadata using package-qualified imports so static analyzers
# (Pylance) can resolve symbols. Keep sys.path updated above to allow alembic
# runtime to import the package when invoked from the repo root.
from vpn_api.database import Base

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger(__name__)
target_metadata = Base.metadata

# Prefer an explicit DATABASE_URL environment variable or the value in
# alembic.ini. Do NOT silently fall back to the application's local
# test sqlite DB (e.g. vpn_api/test.db) because that can cause migrations
# to run against a developer database unintentionally.
env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    config.set_main_option("sqlalchemy.url", env_db_url)
else:
    if not config.get_main_option("sqlalchemy.url"):
        logger.warning(
            "No DATABASE_URL env var and alembic.ini has no sqlalchemy.url; "
            "migrations will fail unless a DB URL is provided."
        )


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
