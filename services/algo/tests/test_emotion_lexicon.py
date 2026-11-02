import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_emotion_lexicon_matches_contract():
    data = json.loads((ROOT / "packages/contract/emotions.v1.json").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "packages/contract/openapi.yaml").read_text(encoding="utf-8"))
    schema = contract["paths"]["/api/emotions/checkins"]["post"]["requestBody"]["content"][
        "application/json"]["schema"]["properties"]
    assert data["version"] == "1.0.0"
    assert [w["code"] for w in data["words"]] == schema["emotion"]["enum"]
    assert len({w["label"] for w in data["words"]}) == 6
    assert [w["displayOrder"] for w in data["words"]] == list(range(1, 7))
    scale = data["intensityScale"]
    assert scale["min"] == schema["intensity"]["minimum"] == 1
    assert scale["max"] == schema["intensity"]["maximum"] == 5
    assert [level["value"] for level in scale["levels"]] == list(range(1, 6))
    assert all(level["label"] and level["description"] for level in scale["levels"])


def test_poc_corpus_has_distinct_categories_and_ids():
    data = json.loads((ROOT / "scripts/w1/poc-cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) == len({c["id"] for c in cases}) == 128
    assert sum(c["expected_word"] is not None for c in cases) == 64
    assert sum(c["expected_word"] is None for c in cases) == 64
    assert len({c["category"] for c in cases}) >= 10
