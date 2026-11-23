from fastapi import APIRouter, HTTPException, Response

from match.models import ScoreRequest, ScoreResponse
from match.scorer import Scorer, ScoreTimeout

router = APIRouter()
scorer = Scorer()


@router.post("/score", responses={
    400: {"description": "Invalid scoring input"},
    413: {"description": "Scoring body exceeds128KiB"},
    503: {"description": "Scoring compute budget exceeded"},
    "4XX": {"description": "Scoring request rejected; validation uses400"},
})
def score(request: ScoreRequest, response: Response) -> ScoreResponse:
    response.headers["X-Score-Config-SHA256"] = scorer.sha256
    try:
        return ScoreResponse.model_validate(scorer.score(request))
    except ScoreTimeout as exc:
        raise HTTPException(status_code=503, detail="Scoring temporarily unavailable") from exc
