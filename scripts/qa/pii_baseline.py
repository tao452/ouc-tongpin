"""Evaluate versioned synthetic expectations, never infer privacy compliance from a regex."""

import hashlib
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

from pii_scan import RULES, scan

KINDS = {"positive", "negative", "review", "out_of_scope"}


def load_corpus(path):
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "origin", "production_acceptance", "rule_names", "cases"}
        or data["version"] != "1.0.0"
        or data["origin"] != "developer-authored-synthetic"
        or data["production_acceptance"] is not False
        or not isinstance(data["rule_names"], list)
        or not all(isinstance(rule, str) for rule in data["rule_names"])
        or sorted(data["rule_names"]) != sorted(RULES)
        or not isinstance(data["cases"], list)
        or not data["cases"]
    ):
        raise ValueError("Invalid synthetic baseline manifest")
    identifiers, texts = set(), set()
    fields = {"id", "kind", "channel", "text", "expected_rules", "note"}
    for row in data["cases"]:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("Invalid baseline row")
        if (
            not all(isinstance(row[key], str) for key in ("id", "kind", "channel", "text", "note"))
            or re.fullmatch(r"PII-\d{3}", row["id"]) is None
            or row["id"] in identifiers
            or row["text"] in texts
            or row["kind"] not in KINDS
            or not row["channel"].strip()
            or not row["note"].strip()
            or len(row["text"]) > 4096
            or any(ch in row["text"] for ch in "\r\n\0")
            or not isinstance(row["expected_rules"], list)
            or not all(isinstance(rule, str) for rule in row["expected_rules"])
            or len(row["expected_rules"]) != len(set(row["expected_rules"]))
            or not set(row["expected_rules"]) <= RULES.keys()
        ):
            raise ValueError("Invalid or duplicate baseline row")
        if bool(row["expected_rules"]) != (row["kind"] in {"positive", "review"}):
            raise ValueError("Row kind and expected candidate rules conflict")
        identifiers.add(row["id"])
        texts.add(row["text"])
    if {row["kind"] for row in data["cases"]} != KINDS:
        raise ValueError("Missing baseline case kind")
    covered = {
        rule for row in data["cases"] if row["kind"] == "positive" for rule in row["expected_rules"]
    }
    if covered != RULES.keys():
        raise ValueError("Every rule needs positive synthetic coverage")
    return data, hashlib.sha256(raw).hexdigest()


def evaluate(data):
    # Exercise the public file scanner: one physical line maps to one synthetic case.
    with tempfile.TemporaryDirectory(prefix="ouc-pii-baseline-") as directory:
        source = Path(directory) / "synthetic-input.txt"
        source.write_text("\n".join(row["text"] for row in data["cases"]) + "\n", encoding="utf-8")
        result = scan([source])
    if result["files_scanned"] != 1 or result["lines_scanned"] != len(data["cases"]):
        raise ValueError("Scanner did not read all fixture lines")
    indexed = {row["line"]: sorted(row["rules"]) for row in result["findings"]}
    if len(indexed) != len(result["findings"]) or any(
        row["file_index"] != 1
        or type(row["line"]) is not int
        or not 1 <= row["line"] <= len(data["cases"])
        or not set(row["rules"]) <= RULES.keys()
        for row in result["findings"]
    ):
        raise ValueError("Scanner returned an invalid finding location/rule")
    cases = []
    for line, row in enumerate(data["cases"], 1):
        expected, observed = sorted(row["expected_rules"]), indexed.get(line, [])
        cases.append(
            {
                "case_id": row["id"],
                "kind": row["kind"],
                "channel": row["channel"],
                "expected_rules": expected,
                "observed_rules": observed,
                "expectation_matches": expected == observed,
            }
        )
    supported = [row for row in cases if row["kind"] != "out_of_scope"]
    mismatches = [row["case_id"] for row in cases if not row["expectation_matches"]]
    per_rule = {}
    for rule in sorted(RULES):
        expected = {row["case_id"] for row in supported if rule in row["expected_rules"]}
        observed = {row["case_id"] for row in supported if rule in row["observed_rules"]}
        per_rule[rule] = {
            "expected_candidate_cases": len(expected),
            "observed_candidate_cases": len(observed),
            "missed_case_ids": sorted(expected - observed),
            "extra_case_ids": sorted(observed - expected),
        }
    return {
        "baseline_version": data["version"],
        "data_origin": data["origin"],
        "production_acceptance": False,
        "scope": "Synthetic offline UTF-8 text fixtures only; no database/network or real users.",
        "cases_total": len(cases),
        "kind_counts": dict(Counter(row["kind"] for row in cases)),
        "candidate_cases": len(result["findings"]),
        "expectations_matched": len(cases) - len(mismatches),
        "mismatched_case_ids": mismatches,
        "baseline_passed": not mismatches,
        "per_rule": per_rule,
        "documented_gap_case_ids": [
            row["case_id"] for row in cases if row["kind"] == "out_of_scope"
        ],
        "limitations": "Expected candidate-rule matches, not real-world precision/recall. "
        "Review examples need human context. Out-of-scope cases are documented gaps, "
        "not negative evidence of privacy risk. No business privacy acceptance claim.",
        "results": cases,
    }
