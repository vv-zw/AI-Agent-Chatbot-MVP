from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine, select

from app.core.database import create_db_and_tables
from app.models import Message, SessionRecord, Todo


def test_legacy_sqlite_schema_is_migrated(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sessions (id CHAR(32) PRIMARY KEY, title VARCHAR(120) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"))
        connection.execute(text("CREATE TABLE messages (id CHAR(32) PRIMARY KEY, session_id CHAR(32) NOT NULL, role VARCHAR(9) NOT NULL, content TEXT NOT NULL, created_at DATETIME NOT NULL)"))
        connection.execute(text("CREATE TABLE tool_calls (id CHAR(32) PRIMARY KEY, session_id CHAR(32) NOT NULL, assistant_message_id CHAR(32), tool_message_id CHAR(32), tool_name VARCHAR(80) NOT NULL, arguments JSON, result JSON, status VARCHAR(9) NOT NULL, error_code VARCHAR(80), error_message TEXT, created_at DATETIME NOT NULL, completed_at DATETIME)"))
        connection.execute(text("CREATE TABLE todos (id CHAR(32) PRIMARY KEY, session_id CHAR(32) NOT NULL, content VARCHAR(500) NOT NULL, is_completed BOOLEAN NOT NULL, created_at DATETIME NOT NULL, completed_at DATETIME)"))
        connection.execute(text("INSERT INTO sessions VALUES ('11111111111111111111111111111111', 'legacy', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))
        connection.execute(text("INSERT INTO messages VALUES ('22222222222222222222222222222222', '11111111111111111111111111111111', 'USER', 'hello', '2026-01-01 00:00:00')"))
        connection.execute(text("INSERT INTO todos VALUES ('33333333333333333333333333333333', '11111111111111111111111111111111', 'legacy todo', 0, '2026-01-01 00:00:00', NULL)"))

    create_db_and_tables(engine)

    inspector = inspect(engine)
    assert "metadata" in {column["name"] for column in inspector.get_columns("messages")}
    assert "role_id" in {column["name"] for column in inspector.get_columns("sessions")}
    tool_columns = {column["name"] for column in inspector.get_columns("tool_calls")}
    assert "message_id" in tool_columns
    assert "assistant_message_id" not in tool_columns
    todo_columns = {column["name"] for column in inspector.get_columns("todos")}
    assert {"title", "status", "updated_at"} <= todo_columns

    with Session(engine) as session:
        session_record = session.exec(select(SessionRecord)).one()
        message = session.exec(select(Message)).one()
        todo = session.exec(select(Todo)).one()
        assert session_record.role_id == "general"
        assert message.metadata_json == {}
        assert todo.title == "legacy todo"
        assert todo.status.value == "pending"
    engine.dispose()
