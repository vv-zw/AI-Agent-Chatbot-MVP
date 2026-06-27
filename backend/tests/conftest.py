import os
from collections.abc import Generator
from pathlib import Path


def pytest_configure() -> None:
    Path(".tmp").mkdir(exist_ok=True)

os.environ["LLM_PROVIDER"] = "mock"
os.environ["OPENAI_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.llm_provider_state import runtime_llm_provider_state
from app.main import app
from app.models import (
    Feedback, KnowledgeChunk, KnowledgeFile, Message, SessionRecord, Todo, ToolCall,
)


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
    get_settings.cache_clear()
    runtime_llm_provider_state.reset("mock")
    with Session(TEST_ENGINE) as session:
        session.exec(delete(Feedback))
        session.exec(delete(KnowledgeChunk))
        session.exec(delete(KnowledgeFile))
        session.exec(delete(ToolCall))
        session.exec(delete(Todo))
        session.exec(delete(Message))
        session.exec(delete(SessionRecord))
        session.commit()
    yield
    get_settings.cache_clear()
    runtime_llm_provider_state.reset("mock")
    with Session(TEST_ENGINE) as session:
        session.exec(delete(Feedback))
        session.exec(delete(KnowledgeChunk))
        session.exec(delete(KnowledgeFile))
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
