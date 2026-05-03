from fastapi.testclient import TestClient
from app.agents.slack_approval import _build_preview_url
from app.main import app


def test_health():
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_preview_url_uses_public_base_url(monkeypatch):
    monkeypatch.setattr("app.agents.slack_approval.settings.app_public_base_url", "https://public.example.com")
    monkeypatch.setattr("app.agents.slack_approval.settings.scheduler_api_base_url", "http://private.internal:8080")

    assert _build_preview_url("run-123") == "https://public.example.com/articles/run-123/preview"
