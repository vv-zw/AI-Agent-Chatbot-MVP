import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import KnowledgeChunk, KnowledgeFile, Message, MessageRole, ToolCall
from conftest import TEST_ENGINE


def upload(client: TestClient, session_id: str, name: str, content: str):
    return client.post(
        f"/api/v1/sessions/{session_id}/knowledge/files",
        files={"file": (name, content.encode("utf-8"), "text/plain")},
    )


def ask(client: TestClient, session_id: str, content: str):
    return client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": content, "provider": "mock"},
    )


def test_upload_txt_and_list_file(client: TestClient, session_id: str) -> None:
    response = upload(client, session_id, "architecture.txt", "项目使用 FastAPI 和 React。\n\n数据库采用 SQLite。")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["filename"] == "architecture.txt"
    assert data["content_type"] == "text/plain"
    assert data["chunk_count"] == 1

    listed = client.get(f"/api/v1/sessions/{session_id}/knowledge/files")
    assert listed.status_code == 200
    assert [item["filename"] for item in listed.json()["data"]] == ["architecture.txt"]


def test_upload_rejects_unsupported_and_empty_files(client: TestClient, session_id: str) -> None:
    unsupported = upload(client, session_id, "payload.py", "print('do not run')")
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    empty = upload(client, session_id, "empty.md", "")
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "EMPTY_FILE"


def test_knowledge_search_persists_call_tool_message_and_citations(client: TestClient, session_id: str) -> None:
    assert upload(client, session_id, "stack.md", "技术栈包括 FastAPI、SQLModel、SQLite 和 React。").status_code == 201
    response = ask(client, session_id, "这个文档里提到了哪些技术栈？")
    assert response.status_code == 201
    data = response.json()["data"]
    call = data["tool_calls"][0]
    assert call["tool_name"] == "knowledge_search"
    assert call["arguments"]["query"] == "这个文档里提到了哪些技术栈？"
    assert call["status"] == "succeeded"
    assert call["result"]["matched_chunks"][0]["filename"] == "stack.md"
    assert "FastAPI" in call["result"]["matched_chunks"][0]["chunk_text"]
    assert "[stack.md]" in data["assistant_message"]["content"]

    with Session(TEST_ENGINE) as db:
        stored = db.exec(select(ToolCall).where(ToolCall.tool_name == "knowledge_search")).one()
        tool_message = db.get(Message, stored.tool_message_id)
        assert tool_message is not None and tool_message.role == MessageRole.TOOL
        assert json.loads(tool_message.content)["result"]["matched_chunks"]


def test_knowledge_search_is_isolated_by_session(client: TestClient) -> None:
    first = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    second = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    assert upload(client, first, "secret.txt", "内部代号是 ORANGE-OWL。 ").status_code == 201

    response = ask(client, second, "根据我上传的文件，内部代号是什么？")
    result = response.json()["data"]["tool_calls"][0]["result"]
    assert result["status"] == "no_files"
    assert result["matched_chunks"] == []
    assert "还没有知识库文件" in response.json()["data"]["assistant_message"]["content"]


def test_no_relevant_chunk_returns_friendly_message(client: TestClient, session_id: str) -> None:
    assert upload(client, session_id, "notes.txt", "苹果和香蕉是常见水果。 ").status_code == 201
    response = ask(client, session_id, "文档中量子计算使用了什么算法？")
    result = response.json()["data"]["tool_calls"][0]["result"]
    assert result["status"] == "no_matches"
    assert result["matched_chunks"] == []
    assert "没有找到" in response.json()["data"]["assistant_message"]["content"]


def test_knowledge_rows_are_deleted_with_session(client: TestClient, session_id: str) -> None:
    assert upload(client, session_id, "delete-me.txt", "删除会话时一起删除。 ").status_code == 201
    assert client.delete(f"/api/v1/sessions/{session_id}").status_code == 200
    with Session(TEST_ENGINE) as db:
        assert db.exec(select(KnowledgeFile)).all() == []
        assert db.exec(select(KnowledgeChunk)).all() == []
