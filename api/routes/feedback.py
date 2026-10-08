from fastapi import APIRouter

from api.schemas.feedback import FeedbackRequest, FeedbackResponse
from api.services.feedback_service import record_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest):
    """Record user feedback on a chat answer and acknowledge receipt.

    Args:
        request: The feedback submission to record.

    Returns:
        A FeedbackResponse acknowledging the submission.
    """
    record_feedback(request)
    return FeedbackResponse()
