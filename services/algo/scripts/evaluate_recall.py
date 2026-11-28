"""Audit explicit v3 rules against development data or a SHA-sealed external corpus.

Reusing PCR/COLD test data is always labelled development/historical, never heldout.
External text stays private; reports contain IDs, hashes, counts and error IDs only.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import ROOT, assess, development, pcr, sha  # noqa: E402
from evaluate_dataset import HttpModerationService, validate_output_path  # noqa: E402

from app.services.moderation import RECALL_DICTIONARY, ModerationService  # noqa: E402


def source_sha(path):
    """Code hashes use Git-style LF across Windows/Linux; data hashes use exact bytes."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_external(path, manifest):
    if sha(path) != manifest["sha256"] or path.stat().st_size != manifest["bytes"]:
        raise ValueError("Sealed dataset bytes differ")
    if manifest["format"] == "pcr":
        rows, exclusions = pcr(path, manifest)
        if exclusions:
            raise ValueError("No external row may silently disappear")
        return rows
    rows = []
    reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")))
    for i, row in enumerate(reader):
        text, label = row[manifest["text_column"]], row[manifest["label_column"]]
        if label not in {"0", "1"} or not isinstance(text, str):
            raise ValueError("Unexpected external labels/schema")
        rows.append(dict(id=f'{manifest["name"]}-{i + 1:05}', text=text,
                         blocked=label == "1", offensive=label == "1",
                         category=row.get(manifest.get("group_column", ""), "ungrouped"),
                         kind="external"))
    if len(rows) != manifest["rows"] or not rows:
        raise ValueError("External row count differs")
    if any(not r["text"].strip() or len(r["text"]) > 2000 for r in rows):
        raise ValueError("Out-of-contract rows must be resolved explicitly, not dropped")
    return rows


def run(dataset, output, manifest_path=None, base_url=None, frozen=False):
    if base_url:
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}
                or url.username is not None or url.password is not None
                or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("Use an isolated local service")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path else None
    paths = [* (ROOT / "services/algo/app/services").glob("*.py"),
             ROOT / "services/algo/app/models/dictionary.py", Path(__file__)]
    hashes = {p.relative_to(ROOT).as_posix(): source_sha(p) for p in paths}
    hashes[RECALL_DICTIONARY.relative_to(ROOT).as_posix()] = sha(RECALL_DICTIONARY)
    if frozen:
        if not manifest or hashes != manifest.get("frozen_artifacts"):
            raise ValueError("Rules or engine changed after evaluation freeze")
        if manifest.get("previously_used", True):
            raise ValueError("Previously used data cannot be called a new heldout")
    validate_output_path(output, [dataset, RECALL_DICTIONARY, *paths,
                                  *([manifest_path] if manifest_path else [])])
    rows = load_external(dataset, manifest) if manifest else development(dataset)
    service = (HttpModerationService(base_url, sha(RECALL_DICTIONARY)) if base_url
               else ModerationService(RECALL_DICTIONARY))
    result = dict(executed_at_utc=datetime.now(UTC).isoformat(),
                  scope="new_external_once" if frozen else "development_or_historical",
                  label_scope="external_broad_offense" if manifest else "literal_rule_mapping",
                  dataset_sha256=sha(dataset), source_manifest=manifest,
                  frozen_artifacts=hashes, mode="http" if base_url else "function",
                  duplicate_rows_kept=len(rows) - len({r["text"] for r in rows}),
                  excluded_rows=0, production_acceptance=False,
                  m1_review="PENDING", m3_reproduction="PENDING",
                  candidate=assess(rows, service, external=bool(manifest)))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Evidence files are immutable: use a new output name for every attempt.
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--base-url")
    parser.add_argument("--frozen-heldout", action="store_true")
    parser.add_argument("--require-broad-thresholds", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.dataset, args.output, args.manifest, args.base_url, args.frozen_heldout)
    except (OSError, ValueError, KeyError, TypeError, TimeoutError):
        print("Evaluation failed: invalid source, frozen artifacts or service", file=sys.stderr)
        return 2
    c = result["candidate"]
    print(json.dumps({k: c[k] for k in ("count", "high_blocking", "any_level")}))
    return int(args.require_broad_thresholds and not (
        c["high_blocking"]["thresholds_met_on_supplied_rows"]
        and c["any_level"]["thresholds_met_on_supplied_rows"]))


if __name__ == "__main__":
    raise SystemExit(main())
