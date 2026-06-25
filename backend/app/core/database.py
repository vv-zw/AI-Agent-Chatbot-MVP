from collections.abc import Generator
from pathlib import Path

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


def create_db_and_tables(database_engine=engine) -> None:
    # Importing models registers SQLModel metadata before create_all.
    from app.models import Message, SessionRecord, Todo, ToolCall  # noqa: F401

    SQLModel.metadata.create_all(database_engine)


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session