from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth.rbac import UnknownUserError, allowed_domains, get_role
from api.db.session import get_db
from api.schemas.access import AccessResponse

router = APIRouter(tags=["access"])


@router.get("/access", response_model=AccessResponse)
def access(username: str, db: Session = Depends(get_db)):
    """Look up a user's role and the domains they are allowed to access.

    Args:
        username: Username to look up.
        db: Database session used to resolve the user's role.

    Returns:
        An AccessResponse containing the username, role, and sorted allowed domains.

    Raises:
        HTTPException: With status 404 if the username is not known.
    """
    try:
        role = get_role(username, db)
    except UnknownUserError as exc:
        raise HTTPException(404, str(exc)) from exc
    return AccessResponse(
        username=username, role=role, allowed_domains=sorted(allowed_domains(role))
    )
