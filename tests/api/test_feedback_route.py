from unittest.mock import patch


def test_feedback_thumbs_up(client):
    payload = {
        "username": "Hsuan US",
        "question": "q",
        "answer": "a",
        "route": "hr_rag",
        "rating": "up",
    }
    with patch("api.routes.feedback.record_feedback") as mock_record:
        resp = client.post("/feedback", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_record.assert_called_once()


def test_feedback_thumbs_down_requires_valid_rating(client):
    payload = {
        "username": "Hsuan US",
        "question": "q",
        "answer": "a",
        "route": "hr_rag",
        "rating": "sideways",
    }
    resp = client.post("/feedback", json=payload)
    assert resp.status_code == 422


def test_feedback_down_with_reason(client):
    payload = {
        "username": "Hsuan US",
        "question": "q",
        "answer": "a",
        "route": "hr_rag",
        "rating": "down",
        "reason": "wrong answer",
    }
    with patch("api.routes.feedback.record_feedback") as mock_record:
        resp = client.post("/feedback", json=payload)
    assert resp.status_code == 200
    mock_record.assert_called_once()
