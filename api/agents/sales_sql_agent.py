import re

from sqlalchemy import inspect, text

from api.agents.llm import get_llm
from api.config import settings
from api.db.session import make_engine

engine = make_engine(settings.sales_readonly_database_url)

SAFE_SELECT_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create)\b|;",
    re.IGNORECASE,
)
# TODO: hardcoded schema works for this small DB; future would need intent detection / schema retrieval
SQL_PROMPT = """You write PostgreSQL SELECT queries. Given this schema:

{schema}

Write a single read-only SELECT statement that answers the question. Do not \
use semicolons, comments, or more than one statement. Return ONLY the SQL, \
no explanation, no markdown fences.

Question: {question}

SQL:"""

SUMMARY_PROMPT = """Question: {question}
SQL used: {sql}
Result rows (truncated): {rows}

Write a short, direct natural-language answer for a sales analyst based on \
these results. If the rows are empty, say so plainly."""


def _schema_description() -> str:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    lines = []
    for table in settings.sales_tables:
        if table not in existing:
            continue
        columns = ", ".join(c["name"] for c in inspector.get_columns(table))
        lines.append(f"{table}({columns})")
    return "\n".join(lines)


def _clean_sql(raw: str) -> str:
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip().rstrip(";").strip()


def _validate(sql: str) -> None:
    if not SAFE_SELECT_RE.match(sql):
        raise ValueError("generated query must start with SELECT or WITH")
    if FORBIDDEN_RE.search(sql):
        raise ValueError("generated query contains a forbidden keyword or ';'")


def answer(question: str) -> dict:
    schema = _schema_description()
    if not schema:
        return {
            "answer": "No sales tables found yet -- run `make fetch-sales` first.",
            "sql": "",
            "rows": [],
        }

    llm = get_llm()
    raw_sql = llm.invoke(SQL_PROMPT.format(schema=schema, question=question)).content
    sql = _clean_sql(raw_sql)

    try:
        _validate(sql)
    except ValueError as exc:
        return {
            "answer": f"I generated an unsafe query and refused to run it ({exc}).",
            "sql": sql,
            "rows": [],
        }

    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = [dict(row._mapping) for row in result.fetchmany(50)]

    summary = llm.invoke(
        SUMMARY_PROMPT.format(question=question, sql=sql, rows=rows[:10])
    ).content

    return {"answer": summary, "sql": sql, "rows": rows}
