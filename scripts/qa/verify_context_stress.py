"""Verify additional synthetic context cases with an explicit candidate dictionary."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "docs/qa/data/us24-context-stress.v1.jsonl"
MANIFEST = ROOT / "docs/qa/data/us24-context-stress.v1.manifest.json"
DICTIONARY = ROOT / "services/algo/app/data/moderation-v3_5-candidate.json"


def verify(output, base_url=None, dictionary=DICTIONARY):
    sys.path.insert(0, str(ROOT / "services/algo/scripts"))
    from evaluate_dataset import HttpModerationService, validate_output_path
    from evaluate_recall import source_sha
    from external_corpus import metrics, record

    from app.services.moderation import ModerationService

    if output.exists():
        raise FileExistsError("Evidence already exists")
    validate_output_path(output, [DATASET, MANIFEST, dictionary, Path(__file__)])
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username or url.password or url.path not in {"", "/"}
                or url.query or url.fragment):
            raise ValueError("Use an isolated local gateway")
    digest = hashlib.sha256(dictionary.read_bytes()).hexdigest()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(DATASET.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Synthetic source differs")
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    if (len(rows) != manifest["rows"] or len({r["id"] for r in rows}) != len(rows)
            or any(type(r["offensive"]) is not bool for r in rows)):
        raise ValueError("Invalid synthetic labels or IDs")
    service = (HttpModerationService(base_url, digest) if base_url
               else ModerationService(dictionary))
    counts = dict(tp=0, fp=0, fn=0, tn=0)
    cases, groups = [], {}
    for row in rows:
        result = service.check(row["text"])
        predicted = bool(result.hits)
        record(counts, predicted, row["offensive"])
        record(groups.setdefault(row["category"], dict(tp=0, fp=0, fn=0, tn=0)),
               predicted, row["offensive"])
        cases.append(dict(id=row["id"], request={"text": row["text"]},
                          response=result.model_dump(), verified=predicted == row["offensive"]))

    def measured(value):
        result = metrics(value)
        result["thresholds_met_on_supplied_rows"] = result.pop("broad_benchmark_thresholds_met")
        return result

    report = dict(scope="additional_synthetic_literal_hit_development", dictionary_sha256=digest,
        source_sha256=manifest["sha256"], mode="http" if base_url else "function",
        engine_sha256={p.relative_to(ROOT).as_posix(): source_sha(p)
                       for p in (ROOT / "services/algo/app/services").glob("*.py")},
        count=len(rows), passed=sum(c["verified"] for c in cases),
        failed=sum(not c["verified"] for c in cases), any_level=measured(counts),
        by_category={k: measured(v) for k, v in groups.items()}, cases=cases,
        counted_in_original120=False, independent_acceptance=False, business_approval="PENDING")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--dictionary", type=Path, default=DICTIONARY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.output, args.base_url, args.dictionary)
    except (OSError, ValueError, KeyError, TypeError):
        print("Context stress verification failed: source or service")
        return 2
    print(json.dumps({k: result[k] for k in ["count", "passed", "failed"]}))
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
