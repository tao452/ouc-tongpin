"""Run the versioned W1 constructed corpus and record reproducible PoC metrics."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/algo"))
from app.services.moderation import ModerationService  # noqa: E402


def run():
    data = Path(__file__).with_name("poc-cases.json").read_bytes()
    cases = json.loads(data)["cases"]
    service = ModerationService()
    results = []
    for case in cases:
        result = service.check(case["text"])
        detected = case["expected_word"] is None or any(
            hit.word == case["expected_word"] for hit in result.hits)
        results.append({"id": case["id"], "category": case["category"],
                        "expected_word_detected": detected, "passed": result.passed,
                        "decision_matches": result.passed == case["expected_passed"]})
    positive = [r for c, r in zip(cases, results, strict=True) if c["expected_word"] is not None]
    benign = [r for c, r in zip(cases, results, strict=True) if c["expected_word"] is None]
    payload = "今天一起去图书馆复习。" * 180
    for _ in range(50):
        service.check(payload)
    elapsed = []
    for _ in range(1000):
        start = time.perf_counter()
        service.check(payload)
        elapsed.append((time.perf_counter() - start) * 1000)
    return {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": platform.python_version(), "platform": platform.platform(),
        "corpus_sha256": hashlib.sha256(data).hexdigest(),
        "dictionary_sha256": service.dictionary_sha256,
        "scope": "W1 developer-constructed PoC; formal business corpus evaluated separately",
        "variant_cases": len(positive),
        "variant_detection_rate": sum(r["expected_word_detected"] for r in positive)/len(positive),
        "benign_cases": len(benign),
        "benign_block_rate": sum(not r["passed"] for r in benign)/len(benign),
        "decision_matches": sum(r["decision_matches"] for r in results),
        "total_cases": len(results),
        "function_benchmark": {"characters": len(payload), "warmup": 50, "iterations": 1000,
                               "p95_ms": sorted(elapsed)[949]},
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "variant_cases", "variant_detection_rate", "benign_cases", "benign_block_rate",
        "decision_matches", "total_cases", "function_benchmark")}, ensure_ascii=False))
    return int(report["decision_matches"] != report["total_cases"] or
               report["variant_detection_rate"] < 0.95 or report["benign_block_rate"] >= 0.02)


if __name__ == "__main__":
    raise SystemExit(main())
