import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import settings

# admin/dev end up identical on purpose -- that's what was asked for
ROLE_DOMAINS: dict[str, set[str]] = {
    "admin": {"hr_rag", "sales_sql", "github"},
    "user": {"hr_rag"},
    "dev": {"hr_rag", "sales_sql", "github"},
    "sales": {"hr_rag", "sales_sql"},
}

_role_cache: dict[str, tuple[str, float]] = {}


class UnknownUserError(Exception):
    pass


# in-memory caching, refresh in 1h
def get_role(username: str, db: Session) -> str:
    cached = _role_cache.get(username)
    if cached and time.monotonic() - cached[1] < settings.role_cache_ttl_seconds:
        return cached[0]

    row = db.execute(
        text("SELECT role FROM users WHERE username = :username"),
        {"username": username},
    ).first()
    if row is None:
        raise UnknownUserError(f"unknown user: {username}")

    _role_cache[username] = (row[0], time.monotonic())
    return row[0]


def allowed_domains(role: str) -> set[str]:
    return ROLE_DOMAINS.get(role, set())
