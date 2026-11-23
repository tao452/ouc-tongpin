"""Fetch a pinned, independently labeled test split into the ignored private directory."""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from dataset_cache import load_pinned

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/qa/data/external/cold-test.v1.json"


def fetch(output, opener=urllib.request.urlopen, refresh=False):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = "https://raw.githubusercontent.com/thu-coai/COLDataset/"
    expected += manifest["revision"] + "/COLDataset/test.csv"
    if manifest["url"] != expected or not 0 < manifest["bytes"] <= 2_000_000:
        raise ValueError("Invalid pinned download metadata")
    if not output.resolve().is_relative_to((ROOT / "qa-private").resolve()):
        raise ValueError("Raw comments belong only in qa-private")
    license_path = MANIFEST.with_name(manifest["license_file"])
    if hashlib.sha256(license_path.read_bytes()).hexdigest() != manifest["license_sha256"]:
        raise ValueError("Upstream license is missing or changed")
    cache = load_pinned(output, manifest, opener, refresh)
    return {**cache, **{key: manifest[key] for key in ("bytes", "sha256", "revision", "rows")
                       if key in manifest}}



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qa-private/cold-test.csv")
    parser.add_argument("--refresh", action="store_true",
                        help="Refresh; fall back to verified cache")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch(args.output, refresh=args.refresh)))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
