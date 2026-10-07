from typing import TypedDict


class ChatState(TypedDict, total=False):
    username: str
    role: str
    allowed_domains: set[str]
    message: str
    route: str
    reason: str
    denied_domain: str
    answer: str
    sql: str | None
    sources: list[str]
