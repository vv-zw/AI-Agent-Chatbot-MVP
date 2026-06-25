import os
from collections.abc import Generator

os.environ["LLM_PROVIDER"] = "mock"
os.environ["OPENAI_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

from app.core.database import get_db_session
from app.main import app
from app.models import Message, SessionRecord, Todo, ToolCall


TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(TEST_ENGINE)


def override_db_session() -> Generator[Session, None, None]:
    with Session(TEST_ENGINE) as session:
        yield session


app.dependency_overrides[get_db_session] = override_db_session


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    with Session(TEST_ENGINE) as session:
        session.exec(delete(ToolCall))
        session.exec(delete(Todo))
        session.exec(delete(Message))
        session.exec(delete(SessionRecord))
        session.commit()
    yield
    with Session(TEST_ENGINE) as session:
        session.exec(delete(ToolCall))
        session.exec(delete(Todo))
        session.exec(delete(Message))
        session.exec(delete(SessionRecord))
        session.commit()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def session_id(client: TestClient) -> str:
    response = client.post("/api/v1/sessions", json={})
    assert response.status_code == 201
    return response.json()["data"]["id"]