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
CODE_FILES = tuple(
    Path(__file__).resolve().with_name(name)
    for name in ("pii_scan.py", "pii_baseline.py", "run_pii_baseline.py")
)


def validate_output_path(output, inputs):
    """Keep report writes from replacing input data or the scanner's own code."""
    if output is None:
        return
    resolved_output = output.resolve()
    for source in (*inputs, *CODE_FILES):
        if resolved_output == source.resolve() or (
            output.exists() and source.exists() and output.samefile(source)
        ):
            raise ValueError("Report output conflicts with an input or code file")


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
        validate_output_path(args.output, args.files)
        result = scan(args.files)
    except (OSError, ValueError):
        print(
            "Scan failed: input is unreadable, not UTF-8 text or output is unsafe", file=sys.stderr
        )
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
