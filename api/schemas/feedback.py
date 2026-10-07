from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    username: str
    question: str
    answer: str
    route: str
    rating: Literal["up", "down"]
    reason: str | None = None


class FeedbackResponse(BaseModel):
    status: str = Field(default="ok")
