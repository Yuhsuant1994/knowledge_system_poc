import logging
import re
from datetime import datetime, timedelta

import psycopg2
import requests

from api.config import settings
from api.core.logging import configure_logging

logger = logging.getLogger(__name__)

DUMP_URL = "https://raw.githubusercontent.com/drizzle-team/drizzle-northwind-benchmarks-pg/main/data/init-db.sql"
TABLES = ("order_details", "orders", "employees", "products", "suppliers", "customers")
TARGET_START = datetime(2026, 1, 1)
TARGET_END = datetime(2026, 9, 30)
DATE_RE = re.compile(r"'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)'")


def _rescale_order_dates(sql: str) -> str:
    # Rescale order dates so they look current
    match = re.search(r"(INSERT INTO orders\(.*?\) VALUES\s*)(.*?)(;)", sql, re.S)
    block = match.group(2)

    dates = [datetime.strptime(m.group(1), "%Y-%m-%d") for m in DATE_RE.finditer(block)]
    min_d, max_d = min(dates), max(dates)
    span = (max_d - min_d).total_seconds() or 1
    target_span = (TARGET_END - TARGET_START).total_seconds()

    def repl(m):
        d = datetime.strptime(m.group(1), "%Y-%m-%d")
        frac = (d - min_d).total_seconds() / span
        new_d = TARGET_START + timedelta(seconds=frac * target_span)
        return f"'{new_d.date()} {m.group(2)}'"

    new_block = DATE_RE.sub(repl, block)
    return sql[: match.start(2)] + new_block + sql[match.end(2) :]


def main() -> None:
    sql = requests.get(DUMP_URL, timeout=30).text
    sql = _rescale_order_dates(sql)

    dsn = settings.database_url.replace("postgresql+psycopg2", "postgresql")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("\n".join(f'DROP TABLE IF EXISTS "{t}" CASCADE;' for t in TABLES))
        cur.execute(sql)
    conn.close()
    logger.info(
        "loaded northwind sales data, order dates rescaled into %s..%s",
        TARGET_START.date(),
        TARGET_END.date(),
    )


if __name__ == "__main__":
    configure_logging()
    main()
