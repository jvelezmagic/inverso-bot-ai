from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GROQ_API_KEY: str

    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    DATABASE_POOL_SIZE: int = 50
    DATABASE_POOL_MAX_OVERFLOW: int = 50

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URI_ASYNCPG(self) -> PostgresDsn:
        """Get SQLAlchemy URI for AI database."""
        url = MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            path=self.DATABASE_NAME,
        )
        return PostgresDsn(url.unicode_string())

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URI_PSYCOPG(self) -> PostgresDsn:
        """Get psycopg URI for AI database."""
        url = MultiHostUrl.build(
            scheme="postgresql",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            path=self.DATABASE_NAME,
        )
        return PostgresDsn(url.unicode_string())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore
