import os
from typing import Generator, Any
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv


load_dotenv(dotenv_path=".env.test")

TEST_POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
TEST_POSTGRES_USER = os.getenv("POSTGRES_USER")
TEST_POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
TEST_POSTGRES_DB = os.getenv("POSTGRES_DB")

SQLALCHEMY_DATABASE_URL_TEST = (
    f"postgresql+psycopg2://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
    f"@{TEST_POSTGRES_SERVER}/{TEST_POSTGRES_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL_TEST)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from db.base import Base, get_db
from main import app
from core.config import settings


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, Any, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def client(db_session: Session) -> Generator[TestClient, Any, None]:
    def override_get_db() -> Generator[Session, Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def auth_token(client: TestClient) -> str:
    test_email = "testuser@example.com"
    test_password = "testpassword"

    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": test_email, "password": test_password},
    )

    # логин
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={"username": test_email, "password": test_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token_data = response.json()
    return f"{token_data['token_type']} {token_data['access_token']}"