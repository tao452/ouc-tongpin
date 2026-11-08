"""Offline candidate-PII scan. Outputs locations/rule names, never matched values."""
import argparse
import json
import re
import sys
from pathlib import Path

RULES = {
    "phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "student_field": re.compile(
        r'''(?i)(?:student_?id|studentNumber|学号)["']?\s*[:=]\s*["']?[a-z0-9-]{6,32}'''),
    "credential_field": re.compile(
        r'''(?i)(?:token|password|secret|openid|session_key)["']?\s*[:=]\s*["']?[a-z0-9._~+/-]{4,}'''),
    "authorization": re.compile(r"(?i)(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]{4,}=*"),
}


def scan(paths):
    findings = []
    lines = 0
    for index, path in enumerate(paths, 1):
        with path.open(encoding="utf-8-sig") as source:
            for line_number, text in enumerate(source, 1):
                if "\0" in text:
                    raise ValueError("Binary input is unsupported")
                lines += 1
                matched = [name for name, rule in RULES.items() if rule.search(text)]
                if matched:
                    findings.append({"file_index": index, "line": line_number, "rules": matched})
    return {
        "files_scanned": len(paths), "lines_scanned": lines, "findings": findings,
        "status": "candidates_found" if findings else "no_rule_matches",
        "limitations": "Candidate regex matches need manual review. No matches does not prove "
                       "No coverage of names, addresses, images, or encrypted fields. "
                       "No database connection was made; scope is only the supplied UTF-8 files.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        result = scan(args.files)
    except (OSError, ValueError):
        print("Scan failed: an input file is unreadable or not UTF-8 text", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
