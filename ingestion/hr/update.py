import logging
from datetime import datetime, timedelta, timezone

import requests

from api.config import settings
from api.core.logging import configure_logging
from ingestion.hr.crawl import extract_title, fetch_doc, list_docs, page_url
from ingestion.hr.store import delete_doc, index_doc

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"


def _recent_changed_paths() -> set[str]:
    since = (
        datetime.now(timezone.utc) - timedelta(days=settings.hr_update_lookback_days)
    ).isoformat()
    url = f"{API_BASE}/repos/{settings.hr_source_repo}/commits"
    commits = requests.get(
        url, params={"path": settings.hr_source_path, "since": since}, timeout=30
    ).json()

    changed = set()
    for commit in commits:
        detail = requests.get(
            f"{API_BASE}/repos/{settings.hr_source_repo}/commits/{commit['sha']}",
            timeout=30,
        ).json()
        for f in detail.get("files", []):
            if f["filename"].startswith(settings.hr_source_path):
                changed.add(f["filename"])
    return changed


def main() -> None:
    # detect recent changes
    changed_paths = _recent_changed_paths()
    if not changed_paths:
        logger.info("no handbook/company changes in the lookback window")
        return

    docs_by_path = {d["path"]: d for d in list_docs()}
    total = 0
    deleted = 0
    # delete the modified docs and reindex the modified doc
    for path in changed_paths:
        doc = docs_by_path.get(path)
        if not doc:
            delete_doc(page_url(path))
            deleted += 1
            continue
        content = fetch_doc(path)
        title = extract_title(content, path)
        total += index_doc(doc["url"], title, content)
    logger.info(
        "re-indexed %d chunks across %d changed files (%d removed)",
        total,
        len(changed_paths),
        deleted,
    )


if __name__ == "__main__":
    configure_logging()
    main()
