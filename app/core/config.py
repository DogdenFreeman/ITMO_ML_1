import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Сервис регистрации посещаемости студентов"
    API_V1_STR: str = "/api/v1"

    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "database")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "user_test")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "default_password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "db_test")
    DATABASE_URL: str | None = None

    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_changed")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    PASSWORD_HASH_SCHEMES: List[str] = ["bcrypt"]

    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "changeme")
    DEMO_USER_EMAIL: str = os.getenv("DEMO_USER_EMAIL", "student@example.com")
    DEMO_USER_PASSWORD: str = os.getenv("DEMO_USER_PASSWORD", "testpass")

    PREDICTION_COST: float = 1.0

    class Config:
        case_sensitive = True
        env_file = '.env'
        env_file_encoding = 'utf-8'

    def __init__(self, **values):
        super().__init__(**values)

        self.DATABASE_URL = f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
