from logging.config import fileConfig
from pathlib import Path
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import DATABASE_URL
from app.db import Base, engine
import app.models  # register every mapped table before configuring metadata

config=context.config
if config.config_file_name:fileConfig(config.config_file_name)
config.set_main_option('sqlalchemy.url', DATABASE_URL.replace('%','%%'))
target_metadata=Base.metadata

def run_migrations_offline():
    context.configure(url=DATABASE_URL,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'},compare_type=True)
    with context.begin_transaction():context.run_migrations()

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()

if context.is_offline_mode():run_migrations_offline()
else:run_migrations_online()
