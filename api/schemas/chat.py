from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    username: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
    route: str
    reason: str = ""
    sql: str | None = None
    sources: list[str]
