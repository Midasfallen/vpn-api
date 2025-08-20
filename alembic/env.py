from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os
# Ensure project root is on sys.path so package imports work (vpn_api)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
try:
    from vpn_api import database
    from vpn_api.database import Base
    from vpn_api import models
except Exception:
    # Fallback: try relative imports for older setups
    import database
    from database import Base
    import models

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
# If alembic.ini doesn't set sqlalchemy.url, prefer the application's DB_URL so
# migrations run against the same database used by the app.
app_db_url = getattr(database, "DB_URL", None)
if app_db_url and not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", app_db_url)

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
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
