"""Validate W3 evidence without turning fixture matches into business acceptance."""

import hashlib
import math
import re
import subprocess
from collections import Counter
from functools import cache

from pii_baseline import load_corpus
from run_w3_api_regression import INPUT_FILES, ROOT, load_manifest, validate_results
from run_w3_load import ENDPOINT, percentile


@cache
def source_hash(revision, name):
    raw = subprocess.check_output(
        ["git", "show", f"{revision}:{name}"], cwd=ROOT, stderr=subprocess.DEVNULL
    )
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(reports, revision):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "Invalid source revision")
    api, pii, load, java = (reports[name] for name in ("api", "pii", "load", "java"))
    for report in reports.values():
        require({report[key] for key in ("source_commit", "source_revision") if key in report}
                == {revision},
                "Mixed or unexpected source revisions")
        require(type(report.get("working_tree_dirty", False)) is bool,
                "Invalid working-tree metadata")
        require(isinstance(report.get("executed_at_utc"), str), "Missing execution time")

    expected = {path.relative_to(ROOT).as_posix() for path in INPUT_FILES}
    require(api["input_sha256"] == {name: source_hash(revision, name) for name in expected},
            "API input hashes do not match the source revision")
    manifest = load_manifest()
    rows = validate_results(api["results"], manifest)
    modules = dict(Counter(row["module"] for row in rows))
    api_counts = dict(Counter(row["status"] for row in rows))
    require(api_counts == {"PASS": 30}, "W3 API cases failed")
    require(api["status_counts"] == api_counts and api["module_counts"] == modules,
            "API summary disagrees with its case results")

    corpus_name = "docs/qa/data/pii-baseline.v1.json"
    corpus, corpus_hash = load_corpus(ROOT / corpus_name)
    require(pii["corpus_sha256"] == corpus_hash == source_hash(revision, corpus_name),
            "PII corpus does not match the source revision")
    pii_files = {f"scripts/qa/{name}.py" for name in
                 ("pii_scan", "pii_baseline", "run_pii_baseline")}
    require(pii["code_sha256"] == {name: source_hash(revision, name) for name in pii_files},
            "PII code hashes do not match the source revision")
    expected_rows = {row["id"]: row for row in corpus["cases"]}
    require(len(pii["results"]) == len(expected_rows) == 62, "Incomplete PII baseline")
    require(len({row["case_id"] for row in pii["results"]}) == 62, "Duplicate PII case")
    for row in pii["results"]:
        expected_row = expected_rows[row["case_id"]]
        require(row["kind"] == expected_row["kind"]
                and row["channel"] == expected_row["channel"]
                and sorted(row["observed_rules"]) == sorted(expected_row["expected_rules"])
                and row["expected_rules"] == row["observed_rules"]
                and row["expectation_matches"] is True, "PII expectation mismatch")
    require(pii["baseline_passed"] is True and pii["expectations_matched"] == 62
            and pii["cases_total"] == 62 and pii["mismatched_case_ids"] == []
            and pii["production_acceptance"] is False, "Invalid PII acceptance claim")

    totals = java["java_test_totals"]
    require(type(totals["tests"]) is int and totals["tests"] > 0
            and all(type(totals[key]) is int and totals[key] == 0
                    for key in ("failures", "errors", "skipped")), "Java tests incomplete")
    privacy = java["catalogue_results"]
    require(len(privacy) == 7 and {row["case_id"] for row in privacy}
            == {f"S1-{n:03}" for n in range(69, 76)}, "Incomplete privacy JUnit cases")
    require(all(row["status"] == "PASS" and row.get("observations") for row in privacy),
            "Privacy JUnit cases failed or lack observations")

    require(load["script_sha256"] == source_hash(revision, "scripts/qa/run_w3_load.py"),
            "Load script does not match the source revision")
    count, concurrency = load["requests"], load["concurrency"]
    require(type(count) is int and 1 <= count <= 1000 and type(concurrency) is int
            and 1 <= concurrency <= min(50, count) and load["endpoint"] == ENDPOINT,
            "Unbounded or unexpected demonstration workload")
    requests = load["results"]
    require(len(requests) == count
            and {row["request_id"] for row in requests} == set(range(1, count + 1)),
            "Missing or duplicate load request")
    require(all(row["status"] == "PASS" and row["http_status"] == 200
                and row["error"] is None and type(row["elapsed_ms"]) in (int, float)
                and math.isfinite(row["elapsed_ms"]) and row["elapsed_ms"] >= 0
                for row in requests), "Load requests failed or contain invalid timings")
    timings = [row["elapsed_ms"] for row in requests]
    latency = {key: percentile(timings, fraction)
               for key, fraction in (("p50", .5), ("p95", .95), ("p99", .99))}
    require(load["status_counts"] == {"PASS": count} and load["error_rate"] == 0
            and load["latency_ms"] == latency, "Load summary disagrees with its requests")
    return {
        "source_revision": revision,
        "automated_checks_passed": True,
        "business_acceptance": False,
        "checks": {
            "java_tests": totals["tests"], "privacy_junit_passed": len(privacy),
            "api_passed": len(rows), "api_modules": modules,
            "pii_expectations_matched": 62,
            "pii_documented_gaps": sum(row["kind"] == "out_of_scope"
                                       for row in corpus["cases"]),
            "demo_requests": count, "demo_concurrency": concurrency,
            "demo_error_rate": 0, "demo_latency_ms": latency,
        },
        "evidence_executed_at_utc": {name: row["executed_at_utc"]
                                     for name, row in reports.items()},
        "evidence_working_tree_dirty": {name: row.get("working_tree_dirty")
                                        for name, row in reports.items()},
        "pending": [
            "Non-author review and merge of the report/CI follow-up PR",
            "M5 trusted identity and authorization integration in the business environment",
            "M1 real-business PII scan and independent review",
            "Actual meeting/demo record; no historical attendance claim",
        ],
        "limitations": "Synthetic-account isolated-stack regression and synthetic PII baseline; "
        "bounded read-only load demonstration, not production capacity or business acceptance. "
        "Issue #25 recognition targets are separate and remain unmet.",
    }
