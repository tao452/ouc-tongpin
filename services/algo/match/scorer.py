import hashlib
import os
import time
from pathlib import Path

from match.features import features
from match.models import ScoreConfig, ScoreRequest

COMPUTE_BUDGET_SECONDS = 0.05
DEFAULT_CONFIG = Path(__file__).with_name("weights.v1.json")


class ScoreTimeout(TimeoutError):
    pass


class Scorer:
    def __init__(self, config_path=None):
        path = config_path or os.environ.get("MATCH_WEIGHT_CONFIG_PATH") or DEFAULT_CONFIG
        raw = Path(path).read_bytes()
        self.config = ScoreConfig.model_validate_json(raw)
        self.sha256 = hashlib.sha256(raw).hexdigest()

    def score(self, request: ScoreRequest):
        deadline = time.perf_counter() + COMPUTE_BUDGET_SECONDS
        rows = []
        weights = self.config.weights
        for candidate in request.items():
            f = features(request.query, candidate, self.config.distance_scale_m)
            value = 100 * (weights.emotion * f["emotion_similarity"]
                           + weights.interests * f["interest_jaccard"]
                           + weights.time * f["time_jaccard"]
                           + weights.distance * f["distance_decay"])
            rows.append({"id": candidate.id, "score": round(value, 6), "features": f})
            if time.perf_counter() > deadline:
                raise ScoreTimeout("Scoring compute budget exceeded")
        return {"items": sorted(rows, key=lambda row: (-row["score"], row["id"])),
                "feature_version": self.config.feature_version,
                "weights_version": self.config.weights_version,
                "config_sha256": self.sha256, "fallback": False}
