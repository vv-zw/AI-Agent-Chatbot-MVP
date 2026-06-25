from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        health.raise_for_status()

        created = client.post("/api/v1/sessions", json={})
        created.raise_for_status()
        session_id = created.json()["data"]["id"]

        sent = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "hello"},
        )
        sent.raise_for_status()

        detail = client.get(f"/api/v1/sessions/{session_id}")
        detail.raise_for_status()
        assert len(detail.json()["data"]["messages"]) == 2

        print("health:", health.json())
        print("session:", session_id)
        print(
            "assistant:",
            sent.json()["data"]["assistant_message"]["content"],
        )


if __name__ == "__main__":
    main()

