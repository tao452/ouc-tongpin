"""Offline candidate-PII scan. Outputs locations/rule names, never matched values."""

import argparse
import json
import re
import sys
from pathlib import Path

RULES = {
    "phone": re.compile(r"(?<!\d)(?:(?:\+86|0086|86)[ -]?)?1[3-9]\d{9}(?!\d)"),
    "identity_number": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "student_field": re.compile(
        r"""(?i)(?<![\w])(?:student_?(?:id|no|number)|学号)"""
        r"""["']?\s*[:=：]\s*["']?[a-z0-9-]{6,32}"""
    ),
    "credential_field": re.compile(
        r"""(?i)(?<![\w])(?:(?:access_?|refresh_?)?token|password|(?:client_?)?secret|"""
        r"""open_?id|session_?key|api_?key)["']?\s*[:=：]\s*["']?[a-z0-9._~+/-]{4,}"""
    ),
    "authorization": re.compile(r"(?i)(?<![\w])(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]{4,}=*"),
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
        "files_scanned": len(paths),
        "lines_scanned": lines,
        "findings": findings,
        "status": "candidates_found" if findings else "no_rule_matches",
        "limitations": "Candidate regex matches need manual review. "
        "A match is not proof of a leak. "
        "No matches does not establish privacy compliance. "
        "No coverage of names, addresses, images, or encrypted fields. "
        "No database connection was made; scope is only the supplied UTF-8 files.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = scan(args.files)
    except (OSError, ValueError):
        print("Scan failed: an input file is unreadable or not UTF-8 text", file=sys.stderr)
        return 2
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8")
        except OSError:
            print("Scan failed: output is not writable", file=sys.stderr)
            return 2
    print(content, end="")
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
