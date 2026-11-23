"""Fetch the sealed PCR-ToxiCN bytes for local evaluation only."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

from dataset_cache import load_pinned

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/qa/data/external/pcr-test.v1.json"


def fetch(output, opener=urllib.request.urlopen, refresh=False):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = ("https://huggingface.co/datasets/UTSNLPGroup/PCR-ToxiCN/resolve/"
                + manifest["revision"] + "/PCR-ToxiCN.json")
    if manifest["url"] != expected or not 0 < manifest["bytes"] < 2_000_000:
        raise ValueError("Unexpected sealed source")
    if not output.resolve().is_relative_to((ROOT / "qa-private").resolve()):
        raise ValueError("Raw data belongs only in qa-private")
    cache = load_pinned(output, manifest, opener, refresh)
    return {**cache, **{key: manifest[key] for key in ("bytes", "sha256", "revision", "rows")}}



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qa-private/pcr-test.json")
    parser.add_argument("--refresh", action="store_true",
                        help="Refresh; fall back to verified cache")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch(args.output, refresh=args.refresh)))
    except (OSError, ValueError, KeyError) as exc:
        print(f"Sealed PCR dataset unavailable: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
