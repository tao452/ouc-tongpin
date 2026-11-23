from fastapi import APIRouter, HTTPException, Response

from match.models import ScoreRequest
from match.scorer import Scorer, ScoreTimeout

router = APIRouter()
scorer = Scorer()


@router.post("/score")
def score(request: ScoreRequest, response: Response):
    response.headers["X-Score-Config-SHA256"] = scorer.sha256
    try:
        return scorer.score(request)
    except ScoreTimeout as exc:
        raise HTTPException(status_code=503, detail="Scoring temporarily unavailable") from exc
