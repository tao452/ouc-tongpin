"""Evaluate user-supplied JSONL labels. Never infer or fabricate ground truth."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.models.moderation import ModerationRequest  # noqa: E402
from app.services.moderation import ModerationService  # noqa: E402


def load_samples(path):
    raw = path.read_bytes()
    records, identifiers = [], set()
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
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f"Invalid or duplicate sample at line {line_number}") from error
        identifiers.add(record["id"])
        records.append(record)
    if not records:
        raise ValueError("Dataset is empty")
    return records, hashlib.sha256(raw).hexdigest()


def evaluate(records, service):
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
    return {
        "samples": len(records), "confusion_matrix": counts, "recall": recall,
        "false_positive_rate": fpr,
        "function_p95_ms": sorted(durations)[math.ceil(len(durations) * 0.95) - 1],
        "both_classes_present": complete,
        "thresholds_met_on_supplied_rows": complete and recall >= 0.95 and fpr < 0.02,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args(argv)
    try:
        records, digest = load_samples(args.dataset)
        service = ModerationService(args.dictionary)
        result = evaluate(records, service)
    except (OSError, ValueError, TypeError):
        print("Evaluation failed: dataset/dictionary is missing or invalid", file=sys.stderr)
        return 2
    result.update({
        "dataset_sha256": digest,
        "dictionary_sha256": service.dictionary_sha256,
        "limitations": "Labels supplied by caller; review/independence not verified. "
                       "Function latency only; no HTTP/concurrency or production acceptance claim.",
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["both_classes_present"]:
        return 2
    return 0 if result["thresholds_met_on_supplied_rows"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
