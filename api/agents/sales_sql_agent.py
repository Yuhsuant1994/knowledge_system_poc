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
    """Build a compact "table(columns)" listing of the configured sales tables.

    Only tables from `settings.sales_tables` that actually exist in the
    database are included.

    Returns:
        One "table(col1, col2, ...)" line per existing table, newline-joined.
    """
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
    """Strip markdown code fences and a trailing semicolon from LLM output.

    Args:
        raw: Raw SQL text as returned by the LLM.

    Returns:
        The cleaned SQL statement.
    """
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip().rstrip(";").strip()


def _validate(sql: str) -> None:
    """Ensure a generated query is a single read-only SELECT/WITH statement.

    Args:
        sql: The SQL statement to validate.

    Raises:
        ValueError: If the statement doesn't start with SELECT/WITH, or
            contains a forbidden keyword or a semicolon.
    """
    if not SAFE_SELECT_RE.match(sql):
        raise ValueError("generated query must start with SELECT or WITH")
    if FORBIDDEN_RE.search(sql):
        raise ValueError("generated query contains a forbidden keyword or ';'")


def answer(question: str) -> dict:
    """Answer a sales question by generating, validating, and running SQL.

    Generates a SELECT statement from the schema and question via the LLM,
    validates it's safe, executes it against the read-only sales database
    (capped at 50 rows), and summarizes the results in natural language.

    Args:
        question: The user's sales question.

    Returns:
        A dict with "answer" text, the "sql" that was run (empty string if
        none), and the resulting "rows".
    """
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

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result.fetchmany(50)]
    except Exception as exc:
        return {
            "answer": f"I generated a query that failed to run ({exc}).",
            "sql": sql,
            "rows": [],
        }

    summary = llm.invoke(
        SUMMARY_PROMPT.format(question=question, sql=sql, rows=rows[:10])
    ).content

    return {"answer": summary, "sql": sql, "rows": rows}
