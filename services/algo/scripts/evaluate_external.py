"""Compare the frozen rule vocabulary with independent upstream COLD test labels."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_dataset import HttpModerationService, validate_output_path  # noqa: E402
from external_corpus import load_corpus, metrics, record  # noqa: E402

from app.services.moderation import ModerationService  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DATA_MANIFEST = ROOT / "docs/qa/data/external/cold-test.v1.json"
FORMAL = ROOT / "services/algo/app/data/moderation-v1.json"
STARTER = FORMAL.with_name("words.json")


def assess(records, service):
    counts = {key: 0 for key in ("tp", "fp", "tn", "fn")}
    candidates, cohorts, timings, levels = dict(counts), {}, [], Counter()
    for row in records:
        started = time.perf_counter()
        result = service.check(row["text"])
        timings.append((time.perf_counter() - started) * 1000)
        record(counts, not result.passed, row["offensive"])
        record(candidates, bool(result.hits), row["offensive"])
        cohort = cohorts.setdefault(row["fine_label"], {key: 0 for key in counts})
        record(cohort, not result.passed, row["offensive"])
        levels.update({hit.level for hit in result.hits})
    return {"high_blocking": metrics(counts), "any_level_candidate": metrics(candidates),
            "upstream_fine_label_cohorts": {key: metrics(value)
                                            for key, value in sorted(cohorts.items())},
            "cases_with_each_hit_level": dict(levels),
            "sequential_p95_ms": sorted(timings)[math.ceil(len(timings) * 0.95) - 1],
            "dictionary_sha256": service.dictionary_sha256}


def provenance():
    names = ["services/algo/scripts/" + name for name in (
        "evaluate_external.py", "external_corpus.py", "evaluate_dataset.py")]
    names += ["services/algo/app/services/moderation.py",
              "services/algo/app/services/normalization.py",
              "services/algo/app/routers/moderation.py",
              "services/algo/app/data/moderation-v1.manifest.json"]
    return {"source_revision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                        for name in names}}


def evaluate(dataset, output, base_url=None):
    protected = [dataset, DATA_MANIFEST, FORMAL, STARTER,
                 FORMAL.with_name("moderation-v1.manifest.json"), Path(__file__)]
    protected += list(Path(__file__).parent.glob("*.py"))
    validate_output_path(output, protected)
    manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(FORMAL.read_bytes()).hexdigest() != manifest["dictionary_frozen_sha256"]:
        raise ValueError("Frozen vocabulary changed; use a new version and evaluation plan")
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username is not None or url.password is not None
                or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("External HTTP evaluation requires an isolated local service")
    records, accounting = load_corpus(dataset, manifest)
    starter = assess(records, ModerationService(STARTER))
    formal_service = (HttpModerationService(base_url, manifest["dictionary_frozen_sha256"])
                      if base_url else ModerationService(FORMAL))
    formal = assess(records, formal_service)
    report = {"executed_at_utc": datetime.now(UTC).isoformat(), **provenance(),
              "dataset": {key: manifest[key] for key in (
                  "name", "repository", "revision", "sha256", "license",
                  "dictionary_frozen_commit", "independence", "sampling", "purpose")},
              "accounting": accounting, "evaluation_completed": True,
              "evaluation_mode": "http" if base_url else "function",
              "starter": starter, "formal_v1": formal,
              "production_acceptance": False,
              "m1_release_review": "pending",
              "limitations": [
                  "External offensive labels remain unchanged; they do not equal S1 HIGH labels.",
                  "Any-level candidates include MEDIUM/LOW that the confirmed policy allows.",
                  "No training or dictionary tuning on these test outcomes; v1 is frozen.",
                  "A successful command means evaluation completed, not broad recall passed.",
                  "Sequential HTTP P95 is not concurrency or production performance.",
              ]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--require-broad-thresholds", action="store_true",
                        help="Exit 1 unless external HIGH recall >=95%% and FPR <2%%")
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.dataset, args.output, args.base_url)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("External evaluation failed: invalid inputs, service or output", file=sys.stderr)
        return 2
    summary = {"eligible_rows": report["accounting"]["eligible_rows"],
               "starter": report["starter"]["high_blocking"],
               "formal_v1": report["formal_v1"]["high_blocking"]}
    print(json.dumps(summary))
    if not report["formal_v1"]["high_blocking"]["broad_benchmark_thresholds_met"]:
        print("External broad-offense thresholds NOT met; production acceptance is false.",
              file=sys.stderr)
    return int(args.require_broad_thresholds
               and not report["formal_v1"]["high_blocking"]["broad_benchmark_thresholds_met"])


if __name__ == "__main__":
    raise SystemExit(main())
