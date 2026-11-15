from fastapi import APIRouter, Response

from app.models.moderation import ModerationRequest, ModerationResponse
from app.services.moderation import ModerationService

router = APIRouter()
service = ModerationService()


@router.post("/api/moderation/check", response_model=ModerationResponse)
def check_content(request: ModerationRequest, response: Response) -> ModerationResponse:
    response.headers["X-Moderation-Dictionary-SHA256"] = service.dictionary_sha256
    return service.check(request.text)
