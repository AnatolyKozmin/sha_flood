import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config
from alembic import context

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = Base.metadata


def get_url() -> str:
    # Если DB_URL явно указан и это не SQLite - используем его
    db = settings.DB_URL
    if "sqlite" not in db.lower():
        # Alembic работает синхронно, поэтому используем psycopg2 вместо asyncpg
        if "asyncpg" in db:
            db = db.replace("asyncpg", "psycopg2")
        return db
    
    # Если DB_URL указывает на SQLite по умолчанию, но есть настройки PostgreSQL - используем PostgreSQL
    # Проверяем, что POSTGRES_HOST установлен (в Docker это будет 'db')
    if settings.POSTGRES_HOST and settings.POSTGRES_HOST != 'localhost':
        # Alembic работает синхронно, поэтому используем psycopg2 вместо asyncpg
        pg_url = settings.postgres_url
        if "asyncpg" in pg_url:
            pg_url = pg_url.replace("asyncpg", "psycopg2")
        return pg_url
    
    # Иначе используем SQLite (но для синхронного режима нужен sqlite3, а не aiosqlite)
    if "aiosqlite" in db:
        db = db.replace("aiosqlite", "sqlite3")
    return db


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
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


