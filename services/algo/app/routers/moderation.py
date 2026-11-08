from fastapi import APIRouter

from app.models.moderation import ModerationRequest, ModerationResponse
from app.services.moderation import ModerationService

router = APIRouter()
service = ModerationService()


@router.post("/api/moderation/check", response_model=ModerationResponse)
def check_content(request: ModerationRequest) -> ModerationResponse:
    return service.check(request.text)
