"""Safe startup diagnostics even when the database fails before any regression."""

import json
from pathlib import Path

from regression_stack import Stack
from us25_privacy_runtime import initialization_log_diagnostics


def main():
    # Raw logs stay in process memory; only fixed flags and numeric error codes persist.
    report = initialization_log_diagnostics(Stack().execute("logs", "--no-color", "mysql"))
    output = Path("qa-private/mysql-initialization.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
