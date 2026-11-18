"""Evaluate user-supplied JSONL labels. Never infer or fabricate ground truth."""
import argparse
import hashlib
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.models.moderation import ModerationRequest, ModerationResponse  # noqa: E402
from app.services.moderation import ModerationService  # noqa: E402


class HttpModerationService:
    dictionary_sha256 = None  # The HTTP contract does not expose the remote dictionary version.

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def check(self, text):
        request = urllib.request.Request(
            self.base_url + "/api/moderation/check",
            data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = ModerationResponse.model_validate(json.load(response), strict=True)
        if result.passed == any(hit.level == "HIGH" for hit in result.hits):
            raise ValueError("Inconsistent remote moderation decision")
        return result


def load_samples(path):
    raw = path.read_bytes()
    records, identifiers, texts = [], set(), set()
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if (set(record) != {"id", "text", "expected_passed"}
                    or not isinstance(record["id"], str) or not record["id"].strip()
                    or record["id"] in identifiers
                    or type(record["expected_passed"]) is not bool):
                raise ValueError
            ModerationRequest(text=record["text"])
            if record["text"] in texts:
                raise ValueError
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f"Invalid or duplicate sample at line {line_number}") from error
        identifiers.add(record["id"])
        texts.add(record["text"])
        records.append(record)
    if not records:
        raise ValueError("Dataset is empty")
    return records, hashlib.sha256(raw).hexdigest()


def evaluate(records, service, min_benign=1, min_blocked=1):
    if min_benign < 1 or min_blocked < 1:
        raise ValueError("Sample requirements must be positive")
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    durations = []
    for record in records:
        started = time.perf_counter()
        blocked = not service.check(record["text"]).passed
        durations.append((time.perf_counter() - started) * 1000)
        expected_blocked = not record["expected_passed"]
        key = ("tp" if expected_blocked else "fp") if blocked else (
            "fn" if expected_blocked else "tn")
        counts[key] += 1
    recall = counts["tp"] / (counts["tp"] + counts["fn"]) if (
        counts["tp"] + counts["fn"]) else None
    fpr = counts["fp"] / (counts["fp"] + counts["tn"]) if (
        counts["fp"] + counts["tn"]) else None
    complete = recall is not None and fpr is not None
    benign = counts["fp"] + counts["tn"]
    blocked = counts["tp"] + counts["fn"]
    sufficient = benign >= min_benign and blocked >= min_blocked
    return {
        "samples": len(records), "confusion_matrix": counts, "recall": recall,
        "benign_samples": benign, "blocked_samples": blocked,
        "minimum_benign_samples": min_benign, "minimum_blocked_samples": min_blocked,
        "sample_requirements_met": sufficient,
        "false_positive_rate": fpr,
        "function_p95_ms": sorted(durations)[math.ceil(len(durations) * 0.95) - 1],
        "both_classes_present": complete,
        "thresholds_met_on_supplied_rows": (
            complete and sufficient and recall >= 0.95 and fpr < 0.02),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--dictionary", type=Path)
    source.add_argument("--base-url", help="Evaluate HTTP responses instead of local functions")
    parser.add_argument("--min-benign", type=int, default=1)
    parser.add_argument("--min-blocked", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        records, digest = load_samples(args.dataset)
        service = (HttpModerationService(args.base_url) if args.base_url
                   else ModerationService(args.dictionary))
        result = evaluate(records, service, args.min_benign, args.min_blocked)
        if args.base_url:
            result["http_p95_ms"] = result.pop("function_p95_ms")
    except (OSError, ValueError, TypeError):
        print("Evaluation failed: dataset/dictionary is missing or invalid", file=sys.stderr)
        return 2
    result.update({
        "dataset_sha256": digest,
        "dictionary_sha256": service.dictionary_sha256,
        "evaluation_mode": "http" if args.base_url else "function",
        "limitations": "Labels supplied by caller; review/independence not verified. "
                       "Sequential samples; no concurrency or production acceptance claim.",
    })
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8")
        except OSError:
            print("Evaluation failed: output is not writable", file=sys.stderr)
            return 2
    print(content, end="")
    if not result["both_classes_present"] or not result["sample_requirements_met"]:
        return 2
    return 0 if result["thresholds_met_on_supplied_rows"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
