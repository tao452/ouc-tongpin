"""核对词条开发映射；整句能力边界样本单独记录，不计入正常样本真阴性。"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import ROOT, development, sha  # noqa: E402
from evaluate_dataset import HttpModerationService, validate_output_path  # noqa: E402
from external_corpus import metrics, record  # noqa: E402

from app.services.moderation import ModerationService  # noqa: E402

DICTIONARY = ROOT / "services/algo/app/data/moderation-v4-lexical-candidate.json"
DATASET = ROOT / "docs/qa/data/us24-development.lexical-v4.jsonl"
PLAN = ROOT / "docs/qa/data/us24-lexical-v4-plan.json"


def audit(dictionary=DICTIONARY, plan_path=PLAN):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    entries = json.loads(dictionary.read_text(encoding="utf-8"))
    if sha(dictionary) != plan["dictionary_sha256"]:
        raise ValueError("Candidate dictionary hash differs from review plan")
    if sha(DATASET) != plan["fixture_sha256"]:
        raise ValueError("Development fixture differs from the frozen review plan")
    if Path(plan["source_dictionary"]).name != plan["source_dictionary"]:
        raise ValueError("Invalid historical reference path")
    old_path = DICTIONARY.parent / plan["source_dictionary"]
    old = json.loads(old_path.read_text(encoding="utf-8"))
    old_map = {f"US24-{i:03}": row for i, row in enumerate(old, 1)}
    if len(old) != 132 or sha(old_path) != plan["source_dictionary_sha256"]:
        raise ValueError("Historical reference changed")
    for name, digest in plan["old_files_sha256"].items():
        if Path(name).name != name or sha(DICTIONARY.parent / name) != digest:
            raise ValueError("Historical rollback artifact changed")
    decisions = ["include", "agree_level", "agree_aliases", "agree_pinyin",
                 "needs_exemption", "m1_comments"]
    rows = plan["entries"]
    if len(entries) != len(rows) or len(rows) != plan["entry_count"]:
        raise ValueError("Review table does not cover the complete dictionary")
    if len({row["candidate_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate candidate IDs")
    for entry, row in zip(entries, rows, strict=True):
        if (len(entry["word"]) < 2 or entry["word"] != row["word"]
                or entry["level"] != row["suggested_level"]):
            raise ValueError("Single-character ban or review mapping mismatch")
        if row["m1_status"] != "PENDING" or any(row[key] for key in decisions):
            raise ValueError("Technical candidate must not invent M1 decisions")
        levels = {old_map[key]["level"] for key in row["source_ids"]}
        if levels and entry["level"] not in levels:
            raise ValueError("Lexical extraction silently changed source severity")
    dispositions = plan["old_dispositions"]
    if (len(dispositions) != 132
            or {row["source_id"] for row in dispositions} != set(old_map)):
        raise ValueError("Each historical rule needs exactly one disposition")
    identifiers = {row["candidate_id"] for row in rows}
    for row in dispositions:
        if (not set(row["target_ids"]) <= identifiers
                or row["m1_status"] != "PENDING" or any(row[key] for key in decisions)
                or row["old_level"] != old_map[row["source_id"]]["level"]):
            raise ValueError("Invalid historical-rule disposition or business decision")
    if plan["production_acceptance"] or plan["independent_evaluation"] != "NOT_RUN":
        raise ValueError("Development curation is not independent business acceptance")
    service = ModerationService(dictionary)  # 加载时同时检查变体冲突和读音数量上限。
    return {"entries": len(entries), "levels": dict(Counter(e["level"] for e in entries)),
            "historical_rules_accounted": 132,
            "dispositions": dict(Counter(r["proposed_action"] for r in dispositions)),
            "rollback_files_unchanged": len(plan["old_files_sha256"]),
            "m1_pending": len(rows), "m1_disposition_pending": 132,
            "blank_decisions": len(decisions) * (len(rows) + 132),
            "pinyin_keys": len(service.pinyin), "variants": len(service.variants),
            "dictionary_sha256": service.dictionary_sha256}


def run(output, base_url=None):
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username or url.password or url.path not in {"", "/"}
                or url.query or url.fragment):
            raise ValueError("Use an isolated local service")
    validate_output_path(output, [DICTIONARY, DATASET, PLAN, Path(__file__)])
    if output.exists():
        raise FileExistsError("Evidence already exists")
    audited = audit()
    rows = development(DATASET)
    service = (HttpModerationService(base_url, sha(DICTIONARY)) if base_url
               else ModerationService(DICTIONARY))
    counts = {key: dict(tp=0, fp=0, fn=0, tn=0) for key in ["high_blocking", "any_level"]}
    by_kind, by_category, failures, errors, trace, probes = {}, {}, [], [], [], []
    categories = {entry["word"]: entry["category"] for entry in json.loads(
        PLAN.read_text(encoding="utf-8"))["entries"]}
    for row in rows:
        item = {key: row[key] for key in ["id", "kind", "category"]}
        item["text_sha256"] = hashlib.sha256(row["text"].encode()).hexdigest()
        scope_probe = row["kind"] == "scope_gap"
        expected = {"high_blocking": row["blocked"], "any_level": bool(row["expected_word"])}
        try:
            response = service.check(row["text"])
            hits = [hit.model_dump() for hit in response.hits]
            predicted = {"high_blocking": not response.passed, "any_level": bool(hits)}
            item.update(predicted, hits=hits)
            mapped = (not hits if not expected["any_level"] else any(
                h["word"] == row["expected_word"] and h["level"] == row["expected_level"]
                for h in hits))
        except (TimeoutError, ValueError, OSError) as exc:
            item["error"] = type(exc).__name__
            errors.append(row["id"])
            predicted = {key: not value for key, value in expected.items()}
            mapped = False
        if scope_probe:
            probes.append(item)
            continue
        if predicted != expected or not mapped:
            failures.append(row["id"])
        for mode, prediction in predicted.items():
            record(counts[mode], prediction, expected[mode])
            content_category = categories.get(row["expected_word"], "正常词面与语境对照")
            for grouping, key in [(by_kind, row["kind"]), (by_category, content_category)]:
                group = grouping.setdefault(key, {}).setdefault(
                    mode, dict(tp=0, fp=0, fn=0, tn=0))
                record(group, prediction, expected[mode])
        trace.append(item)
    def measured(value):
        result = metrics(value)
        result["thresholds_met_on_lexical_rows"] = result.pop("broad_benchmark_thresholds_met")
        return result
    result = dict(executed_at_utc=datetime.now(UTC).isoformat(), audit=audited,
                  scope="author_created_lexical_development", total_rows=len(rows),
                  measured_lexical_rows=len(trace), semantic_scope_probes=len(probes),
                  scope_probe_policy="Recorded separately; never benign TN or semantic PASS",
                  mode="http" if base_url else "function", dictionary_sha256=sha(DICTIONARY),
                  dataset_sha256=sha(DATASET), plan_sha256=sha(PLAN),
                  metrics={key: measured(value) for key, value in counts.items()},
                  by_kind={key: {mode: measured(v) for mode, v in group.items()}
                           for key, group in by_kind.items()},
                  by_category={key: {mode: measured(v) for mode, v in group.items()}
                               for key, group in by_category.items()},
                  failures=failures, errors=errors, trace=trace, scope_probes=probes,
                  literal_development_passed=not failures and not errors,
                  production_acceptance=False, independent_evaluation="NOT_RUN",
                  m1_review="PENDING", m3_reproduction="PENDING")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url")
    args = parser.parse_args(argv)
    try:
        result = run(args.output, args.base_url)
    except (OSError, ValueError, KeyError, TypeError):
        print("Lexical evaluation failed: dictionary, plan, source or local service",
              file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ["total_rows", "measured_lexical_rows",
                     "semantic_scope_probes", "metrics", "failures", "errors"]}))
    return int(not result["literal_development_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
