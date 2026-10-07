import json
from datetime import date, datetime
from pathlib import Path

from api.config import settings
from api.schemas.feedback import FeedbackRequest


def record_feedback(request: FeedbackRequest) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"feedback_{date.today().isoformat()}.log"

    entry = {**request.model_dump(), "timestamp": datetime.now().isoformat()}
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
