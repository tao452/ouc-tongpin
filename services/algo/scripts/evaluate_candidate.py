"""Reproduce candidate rule regression or sealed external PCR diagnostics."""

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_dataset import HttpModerationService, validate_output_path  # noqa: E402
from external_corpus import metrics, record  # noqa: E402

from app.services.moderation import (  # noqa: E402
    CANDIDATE_DICTIONARY,
    DEFAULT_DICTIONARY,
    ModerationService,
)

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def development(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Missing rows or duplicate development IDs")
    for row in rows:
        if (not isinstance(row["blocked"], bool) or not isinstance(row["text"], str)
                or not 1 <= len(row["text"]) <= 2000
                or row["blocked"] != (row["expected_level"] == "HIGH")):
            raise ValueError("Invalid development labels")
    return rows


def pcr(path, manifest):
    if sha(path) != manifest["sha256"] or path.stat().st_size != manifest["bytes"]:
        raise ValueError("External data hash changed")
    source = json.loads(path.read_text(encoding="utf-8"))
    if len(source) != manifest["rows"]:
        raise ValueError("External sample count changed")
    rows, excluded = [], Counter()
    for i, item in enumerate(source):
        text = item["text"]
        if (not isinstance(text, str) or type(item["offensive_label"]) is not int
                or item["offensive_label"] not in {0, 1}
                or item["strategy"] not in {"HR", "AR", "NR", "MR"}):
            raise ValueError("Unexpected external schema or labels")
        if not text.strip() or len(text) > 2000:
            excluded["blank_or_over_2000"] += 1
            continue
        rows.append(dict(id=f"PCR-{i + 1:03}", text=text, blocked=bool(item["offensive_label"]),
                         offensive=bool(item["offensive_label"]), category=item["strategy"],
                         kind="external"))
    return rows, dict(excluded)


def assess(rows, service, external=False):
    def empty():
        return dict.fromkeys(("tp", "fp", "fn", "tn"), 0)
    counts = {"high_blocking": empty(), "any_level": empty()}
    groups, kinds, levels, failures, mapping_failures, timings = {}, {}, Counter(), [], [], []
    for row in rows:
        started = time.perf_counter()
        result = service.check(row["text"])
        timings.append((time.perf_counter() - started) * 1000)
        predicted = {"high_blocking": not result.passed, "any_level": bool(result.hits)}
        expected = {"high_blocking": row["blocked"],
                    "any_level": row["offensive"] if external else bool(row["expected_word"])}
        for name in counts:
            record(counts[name], predicted[name], expected[name])
            for grouping, key in [(groups, row["category"]), (kinds, row["kind"])]:
                target = grouping.setdefault(key, {}).setdefault(name, empty())
                record(target, predicted[name], expected[name])
        levels.update({hit.level for hit in result.hits})
        if not external:
            if predicted != expected:
                failures.append(row["id"])
            if row["expected_word"] and not any(
                    hit.word == row["expected_word"] and hit.level == row["expected_level"]
                    for hit in result.hits):
                mapping_failures.append(row["id"])
    def measured(count):
        value = metrics(count)
        value["thresholds_met_on_supplied_rows"] = value.pop("broad_benchmark_thresholds_met")
        return value

    return {"count": len(rows), **{k: measured(v) for k, v in counts.items()},
            "by_category": {k: {n: measured(c) for n, c in v.items()} for k, v in groups.items()},
            "by_kind": {k: {n: measured(c) for n, c in v.items()} for k, v in kinds.items()},
            "hit_levels": dict(levels), "decision_failure_ids": failures,
            "mapping_failure_ids": mapping_failures,
            "p95_ms": sorted(timings)[math.ceil(len(timings) * .95) - 1],
            "max_ms": max(timings), "dictionary_sha256": service.dictionary_sha256}


def run(dataset, output, manifest_path=None, base_url=None):
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username is not None or url.password is not None
                or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("HTTP evaluation requires an isolated local service")
    code_paths = [*Path(__file__).parent.glob("*.py"),
                  * (ROOT / "services/algo/app/services").glob("*.py"),
                  ROOT / "services/algo/app/models/dictionary.py"]
    inputs = [dataset, DEFAULT_DICTIONARY, CANDIDATE_DICTIONARY, *code_paths]
    if manifest_path:
        inputs.append(manifest_path)
    validate_output_path(output, inputs)
    external = manifest_path is not None
    if external:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, digest in manifest["frozen_artifacts"].items():
            if sha(ROOT / name) != digest:
                raise ValueError("Frozen rule or engine changed after external evaluation plan")
        rows, exclusions = pcr(dataset, manifest)
    else:
        rows, exclusions, manifest = development(dataset), {}, None
    candidate = (HttpModerationService(base_url, sha(CANDIDATE_DICTIONARY)) if base_url
                 else ModerationService(CANDIDATE_DICTIONARY))
    result = dict(executed_at_utc=datetime.now(UTC).isoformat(),
                  scope="external_broad_offense" if external else "development_literal_rules",
                  dataset_sha256=sha(dataset), source_manifest=manifest,
                  exclusions=exclusions,
                  duplicate_texts_kept=len(rows)-len({r['text'] for r in rows}),
                  engine_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in code_paths},
                  mode="http" if base_url else "function", production_acceptance=False,
                  m1_review="PENDING", m3_reproduction="PENDING",
                  candidate=assess(rows, candidate, external),
                  original46_current_engine=assess(rows, ModerationService(DEFAULT_DICTIONARY),
                                                   external))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+"\n").encode())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--external-manifest", type=Path)
    parser.add_argument("--base-url")
    args = parser.parse_args(argv)
    try:
        result = run(args.dataset, args.output, args.external_manifest, args.base_url)
    except (ValueError, OSError, KeyError, TypeError, TimeoutError):
        print("Candidate evaluation failed: invalid input, frozen state or service",
              file=sys.stderr)
        return 2
    candidate = result["candidate"]
    print(json.dumps({k: candidate[k] for k in ("count", "high_blocking", "any_level",
                                                "decision_failure_ids", "mapping_failure_ids")}))
    return int(not args.external_manifest and (
        not candidate["high_blocking"]["thresholds_met_on_supplied_rows"]
        or bool(candidate["mapping_failure_ids"])))


if __name__ == "__main__":
    raise SystemExit(main())
