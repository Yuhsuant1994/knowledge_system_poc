from fastapi import APIRouter

from api.schemas.feedback import FeedbackRequest, FeedbackResponse
from api.services.feedback_service import record_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest):
    record_feedback(request)
    return FeedbackResponse()
