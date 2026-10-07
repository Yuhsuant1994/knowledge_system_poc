import logging

from api.core.logging import configure_logging
from ingestion.hr.crawl import extract_title, fetch_doc, list_docs
from ingestion.hr.store import clear_all, index_doc

logger = logging.getLogger(__name__)


def main() -> None:
    clear_all()
    docs = list_docs()
    total = 0
    for doc in docs:
        content = fetch_doc(doc["path"])
        title = extract_title(content, doc["path"])
        total += index_doc(doc["url"], title, content)
    logger.info("indexed %d chunks from %d docs", total, len(docs))


if __name__ == "__main__":
    configure_logging()
    main()
