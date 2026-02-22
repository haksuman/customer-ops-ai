from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Intent
from app.services.extractor import ExtractionResult

client = TestClient(app)


def _mock_llm(reply: str = "Hello,\n\nThank you.\n\nKind regards,\nAI Service Assistant"):
    fake = MagicMock()
    fake.content = reply
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = fake
    mock_llm.with_structured_output.return_value.invoke.return_value = ExtractionResult(
        intents=[Intent.PRODUCT_INFO_REQUEST]
    )
    return mock_llm


def test_process_message_contract():
    with patch("app.core.llm.get_llm", return_value=_mock_llm()):
        payload = {"thread_id": "api-thread-1", "message": "Tell me about dynamic tariff options."}
        response = client.post("/api/messages/process", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "api-thread-1"
    assert "assistant_reply" in body
    assert isinstance(body["workflow_steps"], list)


def test_get_thread_returns_state():
    with patch("app.core.llm.get_llm", return_value=_mock_llm()):
        payload = {"thread_id": "api-thread-2", "message": "Hello, thanks for your support."}
        client.post("/api/messages/process", json=payload)
    response = client.get("/api/threads/api-thread-2")
    assert response.status_code == 200
    assert response.json()["state"]["thread_id"] == "api-thread-2"
