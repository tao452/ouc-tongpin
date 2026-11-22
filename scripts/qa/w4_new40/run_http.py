import argparse
import json

from buddy_rule_cases import register as buddy_rule_cases
from common import Suite
from http_cases import register as http_cases
from moderation_cases import register as moderation_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    suite = Suite(args.project, args.output)
    initial = suite.require_empty()
    suite.initial_counts = initial
    suite.record({"kind": "initial_empty_database", "counts": initial})
    http_cases(suite)
    moderation_cases(suite)
    buddy_rule_cases(suite)
    suite.save()
    print(
        json.dumps(
            {
                "attempted": sum(r.get("executed", False) for r in suite.results),
                "statuses": {
                    status: sum(r["status"] == status for r in suite.results)
                    for status in ["PASS", "FAIL", "BLOCKED", "NOT_RUN"]
                },
            }
        )
    )


if __name__ == "__main__":
    main()
