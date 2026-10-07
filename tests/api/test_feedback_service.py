import json
from dataclasses import replace
from datetime import date

from api.schemas.feedback import FeedbackRequest
from api.services import feedback_service


def test_record_feedback_writes_dated_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(
        feedback_service,
        "settings",
        replace(feedback_service.settings, log_dir=str(tmp_path)),
    )
    request = FeedbackRequest(
        username="Hsuan US",
        question="q",
        answer="a",
        route="hr_rag",
        rating="down",
        reason="bad",
    )

    feedback_service.record_feedback(request)

    path = tmp_path / f"feedback_{date.today().isoformat()}.log"
    assert path.exists()
    entry = json.loads(path.read_text().strip())
    assert entry["username"] == "Hsuan US"
    assert entry["rating"] == "down"
    assert entry["reason"] == "bad"
    assert "timestamp" in entry
