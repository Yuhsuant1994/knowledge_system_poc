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
    """Look up a user's role, using an in-memory cache to avoid repeat queries.

    Args:
        username: Username to look up.
        db: Database session used to query the `users` table on a cache miss.

    Returns:
        The user's role.

    Raises:
        UnknownUserError: If no user with this username exists.
    """
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
    """Get the set of agent domains a role may access.

    Args:
        role: Role name to look up.

    Returns:
        The domains allowed for this role, or an empty set if the role is unknown.
    """
    return ROLE_DOMAINS.get(role, set())
