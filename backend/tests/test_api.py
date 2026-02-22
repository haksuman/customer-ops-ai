from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_process_message_contract():
    payload = {"thread_id": "thread-1", "message": "Tell me about dynamic tariff options."}
    response = client.post("/api/messages/process", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "thread-1"
    assert "assistant_reply" in body
    assert isinstance(body["workflow_steps"], list)


def test_get_thread_returns_state():
    payload = {"thread_id": "thread-2", "message": "Hello, thanks for your support."}
    client.post("/api/messages/process", json=payload)
    response = client.get("/api/threads/thread-2")
    assert response.status_code == 200
    assert response.json()["state"]["thread_id"] == "thread-2"
