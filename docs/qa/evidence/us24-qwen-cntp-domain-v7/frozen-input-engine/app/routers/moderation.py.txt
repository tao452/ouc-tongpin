from fastapi import APIRouter, HTTPException, Response

from app.models.moderation import ModerationRequest, ModerationResponse
from app.services.moderation import ModerationInputError, ModerationService

router = APIRouter()
service = ModerationService()


@router.post("/api/moderation/check", response_model=ModerationResponse)
def check_content(request: ModerationRequest, response: Response) -> ModerationResponse:
    response.headers["X-Moderation-Dictionary-SHA256"] = service.dictionary_sha256
    try:
        return service.check(request.text)
    except ModerationInputError as exc:
        raise HTTPException(status_code=400, detail="Invalid moderation input") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="Moderation temporarily unavailable") from exc
