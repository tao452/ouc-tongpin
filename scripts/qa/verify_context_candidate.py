"""Verify the opt-in v3.1 dictionary through an actual local HTTP gateway."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]

DICTIONARY = ROOT / "services/algo/app/data/moderation-v3_1-candidate.json"
CASES = [
    ("我觉得自己一无是处，我是不是废物，想求助", True, set()),
    ("我是不是废物，想求助。杀了你", False, {("杀了你", "HIGH")}),
    ("我是不是废物，想求助。你是废物", True, {("废物", "MEDIUM")}),
    ("我想求助，你就是鲨币", False, {("傻逼", "HIGH")}),
    ("USB sbatch q4_report nmsl_func", True, set()),
    ('举报：“你妈死了”请处理', True, set()),
    ('举报：“你妈死了”请处理。你妈死了', False, {("你妈死了", "HIGH")}),
    ("你是废物利用活动的志愿者吗", True, set()),
]


def verify(base_url, output):
    sys.path.insert(0, str(ROOT / "services/algo/scripts"))
    from evaluate_dataset import HttpModerationService, validate_output_path

    url = urlsplit(base_url)
    if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
            or url.username or url.password or url.path not in {"", "/"}
            or url.query or url.fragment):
        raise ValueError("Use an isolated local gateway")
    validate_output_path(output, [DICTIONARY])
    if output.exists():
        raise FileExistsError("Evidence already exists")
    digest = hashlib.sha256(DICTIONARY.read_bytes()).hexdigest()
    service = HttpModerationService(base_url, digest)
    cases = []
    for index, (text, passed, expected_hits) in enumerate(CASES, 1):
        result = service.check(text)
        hits = {(h.word, h.level) for h in result.hits}
        cases.append({"id": f"CONTEXT-HTTP-{index:02}", "request": {"text": text},
                          "response": result.model_dump(),
                          "verified": result.passed == passed and hits == expected_hits})
    report = {"scope": "v3_1_synthetic_http_regression", "dictionary_sha256": digest,
                  "count": len(cases), "passed": sum(c["verified"] for c in cases),
                  "failed": sum(not c["verified"] for c in cases), "cases": cases,
                  "counted_in_original120": False, "business_approval": "PENDING"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.base_url, args.output)
    except (OSError, ValueError, KeyError, TypeError):
        print("Context HTTP verification failed")
        return 2
    print(json.dumps({k: result[k] for k in ["count", "passed", "failed"]}))
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
