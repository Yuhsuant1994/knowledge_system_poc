from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.agents.router import get_graph
from api.auth.rbac import UnknownUserError, allowed_domains, get_role


async def run_chat(username: str, message: str, db: Session) -> dict:
    try:
        role = get_role(username, db)
    except UnknownUserError as exc:
        raise HTTPException(404, str(exc)) from exc

    state = {
        "username": username,
        "role": role,
        "allowed_domains": allowed_domains(role),
        "message": message,
    }
    result = await get_graph().ainvoke(state)
    return {
        "answer": result.get("answer", ""),
        "route": result.get("route", "none"),
        "reason": result.get("reason", ""),
        "sql": result.get("sql"),
        "sources": result.get("sources", []),
    }
