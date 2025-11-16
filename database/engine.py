from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings

# Выбираем базу данных:
# 1. Если DB_URL явно указан и это не SQLite - используем его
# 2. Если DB_URL указывает на SQLite по умолчанию, но есть настройки PostgreSQL (в Docker) - используем PostgreSQL
# 3. Иначе используем SQLite
db_url = settings.DB_URL
if 'sqlite' in db_url.lower():
    # Если DB_URL указывает на SQLite, но есть настройки PostgreSQL (в Docker POSTGRES_HOST будет 'db')
    if settings.POSTGRES_HOST and settings.POSTGRES_HOST != 'localhost':
        db_url = settings.postgres_url
else:
    # Если DB_URL явно указан и это не SQLite - используем его
    db_url = settings.DB_URL

engine = create_async_engine(db_url, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session