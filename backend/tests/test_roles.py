import pytest
from fastapi.testclient import TestClient


EXPECTED_ROLE_IDS = ["general", "code", "writing", "interview"]


def test_get_roles_returns_presets(client: TestClient) -> None:
    response = client.get("/api/v1/roles")

    assert response.status_code == 200
    roles = response.json()["data"]
    assert [role["role_id"] for role in roles] == EXPECTED_ROLE_IDS
    assert all(role["name"] and role["description"] and role["system_prompt"] for role in roles)


def test_create_session_uses_general_role_by_default(client: TestClient) -> None:
    response = client.post("/api/v1/sessions", json={})

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role_id"] == "general"
    assert data["role"]["name"] == "通用助手"


def test_create_session_with_specified_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sessions",
        json={"title": "代码讨论", "role_id": "code"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role_id"] == "code"
    assert data["role"]["name"] == "代码助手"


def test_invalid_role_id_returns_unified_error(client: TestClient) -> None:
    response = client.post("/api/v1/sessions", json={"role_id": "unknown"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "ROLE_NOT_FOUND"
    assert payload["error"]["details"] == {"role_id": "unknown"}


def test_update_current_session_role_is_persisted(
    client: TestClient,
    session_id: str,
) -> None:
    response = client.patch(
        f"/api/v1/sessions/{session_id}/role",
        json={"role_id": "writing"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["role_id"] == "writing"
    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert detail["role"]["name"] == "写作助手"


@pytest.mark.parametrize(
    ("role_id", "expected_marker"),
    [
        ("code", "技术视角"),
        ("writing", "表达视角"),
        ("interview", "面试视角"),
    ],
)
def test_mock_reply_reflects_session_role(
    client: TestClient,
    role_id: str,
    expected_marker: str,
) -> None:
    created = client.post("/api/v1/sessions", json={"role_id": role_id})
    session_id = created.json()["data"]["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "请给我一些建议"},
    )

    assert response.status_code == 201
    assert expected_marker in response.json()["data"]["assistant_message"]["content"]


def test_mock_tool_result_keeps_current_role(client: TestClient) -> None:
    created = client.post("/api/v1/sessions", json={"role_id": "code"})
    session_id = created.json()["data"]["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "时间"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["tool_calls"][0]["tool_name"] == "get_current_time"
    assert "Mock - 代码助手" in data["assistant_message"]["content"]


def test_mock_capability_reply_keeps_current_role(client: TestClient) -> None:
    created = client.post("/api/v1/sessions", json={"role_id": "writing"})
    session_id = created.json()["data"]["id"]

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "你都能做什么"},
    )

    assert response.status_code == 201
    assert "Mock - 写作助手" in response.json()["data"]["assistant_message"]["content"]
