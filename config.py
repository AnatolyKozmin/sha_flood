from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')
    
    # Database settings
    DB_URL: str = Field(default='sqlite+aiosqlite:///./bot.db', env='DB_URL')
    
    # Для PostgreSQL можно использовать отдельные переменные
    POSTGRES_DB: str = Field(default='vshu_db', env='POSTGRES_DB')
    POSTGRES_USER: str = Field(default='vshu', env='POSTGRES_USER')
    POSTGRES_PASSWORD: str = Field(default='1234', env='POSTGRES_PASSWORD')
    POSTGRES_HOST: str = Field(default='db', env='POSTGRES_HOST')
    POSTGRES_PORT: int = Field(default=5432, env='POSTGRES_PORT')
    
    ADMIN_IDS: list[int] = Field(default_factory=list, env='ADMIN_IDS')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
    
    @property
    def postgres_url(self) -> str:
        """Формирует URL для PostgreSQL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()

