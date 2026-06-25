from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()

if settings.database_url.startswith("sqlite:///"):
    database_path = settings.database_url.removeprefix("sqlite:///")
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)


def _column_names(database_engine: Engine, table: str) -> set[str]:
    return {
        column["name"]
        for column in inspect(database_engine).get_columns(table)
    }


def _prepare_legacy_sqlite(database_engine: Engine) -> bool:
    if database_engine.dialect.name != "sqlite":
        return False

    tables = set(inspect(database_engine).get_table_names())
    migrate_todos = False
    with database_engine.begin() as connection:
        if "messages" in tables and "metadata" not in _column_names(
            database_engine, "messages"
        ):
            connection.execute(
                text(
                    "ALTER TABLE messages ADD COLUMN metadata JSON "
                    "NOT NULL DEFAULT '{}'"
                )
            )

        if "tool_calls" in tables:
            tool_columns = _column_names(database_engine, "tool_calls")
            if "assistant_message_id" in tool_columns and "message_id" not in tool_columns:
                connection.execute(
                    text(
                        "ALTER TABLE tool_calls "
                        "RENAME COLUMN assistant_message_id TO message_id"
                    )
                )

        if "todos_legacy" in tables:
            if "todos" in tables:
                connection.execute(text("DROP TABLE todos"))
            for index in inspect(database_engine).get_indexes("todos_legacy"):
                connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))
            migrate_todos = True
        elif "todos" in tables:
            todo_columns = _column_names(database_engine, "todos")
            if "content" in todo_columns and "title" not in todo_columns:
                for index in inspect(database_engine).get_indexes("todos"):
                    connection.execute(text(f'DROP INDEX IF EXISTS "{index["name"]}"'))
                connection.execute(text("ALTER TABLE todos RENAME TO todos_legacy"))
                migrate_todos = True
    return migrate_todos


def _finish_legacy_todo_migration(database_engine: Engine) -> None:
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO todos "
                "(id, session_id, title, status, created_at, updated_at) "
                "SELECT id, session_id, content, "
                "CASE WHEN is_completed = 1 THEN 'COMPLETED' ELSE 'PENDING' END, "
                "created_at, COALESCE(completed_at, created_at) "
                "FROM todos_legacy"
            )
        )
        connection.execute(text("DROP TABLE todos_legacy"))


def create_db_and_tables(database_engine: Engine = engine) -> None:
    # Importing models registers SQLModel metadata before create_all.
    from app.models import Message, SessionRecord, Todo, ToolCall  # noqa: F401

    migrate_todos = _prepare_legacy_sqlite(database_engine)
    SQLModel.metadata.create_all(database_engine)
    if migrate_todos:
        _finish_legacy_todo_migration(database_engine)


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session