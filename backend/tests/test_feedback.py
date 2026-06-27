from uuid import uuid4

from fastapi.testclient import TestClient


def create_messages(client: TestClient, session_id: str) -> tuple[str, str]:
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "请给出一个简短回答"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    return data["user_message"]["id"], data["assistant_message"]["id"]


def feedback_url(session_id: str, message_id: str) -> str:
    return f"/api/v1/sessions/{session_id}/messages/{message_id}/feedback"


def test_like_assistant_message(client: TestClient, session_id: str) -> None:
    _, assistant_id = create_messages(client, session_id)

    response = client.post(
        feedback_url(session_id, assistant_id),
        json={"rating": "like"},
    )

    assert response.status_code == 200
    feedback = response.json()["data"]
    assert feedback["message_id"] == assistant_id
    assert feedback["session_id"] == session_id
    assert feedback["rating"] == "like"
    assert feedback["reason"] == ""
    assert feedback["created_at"]
    assert feedback["updated_at"]


def test_dislike_assistant_message_with_reason(
    client: TestClient,
    session_id: str,
) -> None:
    _, assistant_id = create_messages(client, session_id)

    response = client.post(
        feedback_url(session_id, assistant_id),
        json={"rating": "dislike", "reason": "回答不够准确"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["rating"] == "dislike"
    assert response.json()["data"]["reason"] == "回答不够准确"


def test_feedback_on_user_message_fails(
    client: TestClient,
    session_id: str,
) -> None:
    user_id, _ = create_messages(client, session_id)

    response = client.post(
        feedback_url(session_id, user_id),
        json={"rating": "like"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_NOT_ALLOWED"
    assert response.json()["error"]["details"]["role"] == "user"


def test_feedback_on_missing_message_fails(
    client: TestClient,
    session_id: str,
) -> None:
    missing_id = str(uuid4())

    response = client.post(
        feedback_url(session_id, missing_id),
        json={"rating": "like"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MESSAGE_NOT_FOUND"


def test_invalid_feedback_rating_fails(
    client: TestClient,
    session_id: str,
) -> None:
    _, assistant_id = create_messages(client, session_id)

    response = client.post(
        feedback_url(session_id, assistant_id),
        json={"rating": "neutral"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_feedback_reason_too_long_fails(
    client: TestClient,
    session_id: str,
) -> None:
    _, assistant_id = create_messages(client, session_id)

    response = client.post(
        feedback_url(session_id, assistant_id),
        json={"rating": "dislike", "reason": "x" * 501},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_repeated_feedback_updates_existing_record(
    client: TestClient,
    session_id: str,
) -> None:
    _, assistant_id = create_messages(client, session_id)
    url = feedback_url(session_id, assistant_id)
    first = client.post(url, json={"rating": "like"}).json()["data"]

    second_response = client.post(
        url,
        json={"rating": "dislike", "reason": "需要补充依据"},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]
    assert second["rating"] == "dislike"
    assert second["reason"] == "需要补充依据"

    detail = client.get(f"/api/v1/sessions/{session_id}")
    messages = detail.json()["data"]["messages"]
    assistant = next(item for item in messages if item["id"] == assistant_id)
    assert assistant["feedback"]["id"] == first["id"]
    assert assistant["feedback"]["rating"] == "dislike"


def test_message_must_belong_to_current_session(client: TestClient) -> None:
    first_session = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    second_session = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    _, assistant_id = create_messages(client, first_session)

    response = client.post(
        feedback_url(second_session, assistant_id),
        json={"rating": "like"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MESSAGE_SESSION_MISMATCH"
