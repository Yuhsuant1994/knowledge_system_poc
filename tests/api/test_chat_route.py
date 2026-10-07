from unittest.mock import AsyncMock, patch


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_returns_answer(client):
    fake_result = {
        "answer": "hi",
        "route": "hr_rag",
        "reason": "only hr_rag is accessible",
        "sql": None,
        "sources": [],
    }
    with patch("api.routes.chat.run_chat", new=AsyncMock(return_value=fake_result)):
        resp = client.post("/chat", json={"username": "Hsuan US", "message": "hello"})
    assert resp.status_code == 200
    assert resp.json() == fake_result


def test_chat_includes_sql_for_sales_route(client):
    fake_result = {
        "answer": "42 orders",
        "route": "sales_sql",
        "reason": "sales question",
        "sql": "SELECT 1",
        "sources": [],
    }
    with patch("api.routes.chat.run_chat", new=AsyncMock(return_value=fake_result)):
        resp = client.post(
            "/chat", json={"username": "Hsuan SA", "message": "how many orders"}
        )
    assert resp.status_code == 200
    assert resp.json()["sql"] == "SELECT 1"


def test_chat_requires_message(client):
    resp = client.post("/chat", json={"username": "Hsuan US"})
    assert resp.status_code == 422


def test_chat_rejects_empty_message(client):
    resp = client.post("/chat", json={"username": "Hsuan US", "message": ""})
    assert resp.status_code == 422
