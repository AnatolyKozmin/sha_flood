from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings

# Используем DB_URL, если указан, иначе формируем PostgreSQL URL
db_url = settings.DB_URL
if 'sqlite' not in db_url:
    # Если не SQLite, используем PostgreSQL настройки
    db_url = settings.postgres_url

engine = create_async_engine(db_url, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session