"""Evaluate an explicit dictionary version; reused corpora remain historical."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import ROOT, assess, development, sha  # noqa: E402
from evaluate_dataset import HttpModerationService, validate_output_path  # noqa: E402
from evaluate_recall import load_external, source_sha  # noqa: E402

from app.services.moderation import ModerationService  # noqa: E402


def run(dataset, dictionary, output, base_url=None, historical_manifest=None):
    if output.exists():
        raise FileExistsError("Evidence already exists")
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username or url.password or url.path not in {"", "/"}
                or url.query or url.fragment):
            raise ValueError("Use an isolated local service")
    paths = [*(ROOT / "services/algo/app/services").glob("*.py"),
             ROOT / "services/algo/app/models/dictionary.py", Path(__file__)]
    validate_output_path(output, [dataset, dictionary, *paths,
                                 *([historical_manifest] if historical_manifest else [])])
    if historical_manifest:
        manifest = json.loads(historical_manifest.read_text(encoding="utf-8"))
        rows = load_external(dataset, manifest)
    else:
        rows = development(dataset)
    service = (HttpModerationService(base_url, sha(dictionary)) if base_url
               else ModerationService(dictionary))
    result = dict(executed_at_utc=datetime.now(UTC).isoformat(),
                  scope="historical_development" if historical_manifest else "development_literal",
                  label_scope="broad_offense" if historical_manifest else "literal_rule_mapping",
                  source_sha256=sha(dataset), dictionary_sha256=sha(dictionary),
                  code_sha256={p.relative_to(ROOT).as_posix(): source_sha(p) for p in paths},
                  excluded_rows=0, mode="http" if base_url else "function",
                  candidate=assess(rows, service, external=bool(historical_manifest)),
                  production_acceptance=False, m1_review="PENDING", m3_reproduction="PENDING")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--dictionary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--historical-manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.dataset, args.dictionary, args.output, args.base_url,
                     args.historical_manifest)
    except (OSError, ValueError, KeyError, TypeError, TimeoutError):
        print("Version evaluation failed: source, dictionary or local service", file=sys.stderr)
        return 2
    measured = result["candidate"]
    print(json.dumps({k: measured[k] for k in ["count", "high_blocking", "any_level"]}))
    return int(not (measured["high_blocking"]["thresholds_met_on_supplied_rows"]
                    and measured["any_level"]["thresholds_met_on_supplied_rows"]
                    and not measured["mapping_failure_ids"]))


if __name__ == "__main__":
    raise SystemExit(main())
