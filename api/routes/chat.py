from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.schemas.chat import ChatRequest, ChatResponse
from api.services.chat_service import run_chat

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return await run_chat(request.username, request.message, db)
