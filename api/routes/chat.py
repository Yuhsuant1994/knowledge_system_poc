from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.schemas.chat import ChatRequest, ChatResponse
from api.services.chat_service import run_chat

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    """Report a simple liveness status for the API.

    Returns:
        A dict with a status key set to "ok".
    """
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Run a chat message through the agent graph and return the response.

    Args:
        request: The incoming chat request with username and message.
        db: Database session used to resolve the user's role and permissions.

    Returns:
        The chat response produced by running the agent graph.
    """
    return await run_chat(request.username, request.message, db)
