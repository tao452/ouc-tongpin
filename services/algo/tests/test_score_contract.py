from pathlib import Path

import yaml

from app.main import app
from match.models import ScoreRequest, ScoreResponse

CONTRACT = Path(__file__).resolve().parents[3] / "packages/contract/openapi.yaml"


def replace_refs(value):
    if isinstance(value, dict):
        return {k: replace_refs(v) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_refs(v) for v in value]
    return (value.replace("#/$defs/", "#/components/schemas/Match")
            if isinstance(value, str) else value)


def test_internal_score_contract_matches_runtime_schema_and_validation_status():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    operation = contract["paths"]["/score"]["post"]
    assert operation["x-internal"] is True and operation["security"] == []
    assert set(operation["responses"]) == {"200", "400", "413", "503"}
    live = app.openapi()["paths"]["/score"]["post"]
    assert "400" in live["responses"] and "422" not in live["responses"]
    for model in [ScoreRequest, ScoreResponse]:
        schema = model.model_json_schema()
        definitions = schema.pop("$defs", {})
        definitions[model.__name__] = schema
        for name, value in definitions.items():
            assert contract["components"]["schemas"]["Match" + name] == replace_refs(value)


def test_public_gateway_blocks_internal_score_and_container_contains_feature_package():
    root = CONTRACT.parents[2]
    assert "location = /score { return 404; }" in (root / "infra/nginx.conf").read_text()
    assert "COPY match ./match" in (root / "services/algo/Dockerfile").read_text()
