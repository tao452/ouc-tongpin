"""Fetch the sealed PCR-ToxiCN bytes for local evaluation only."""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/qa/data/external/pcr-test.v1.json"


def fetch(output):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = ("https://huggingface.co/datasets/UTSNLPGroup/PCR-ToxiCN/resolve/"
                + manifest["revision"] + "/PCR-ToxiCN.json")
    if manifest["url"] != expected or not 0 < manifest["bytes"] < 2_000_000:
        raise ValueError("Unexpected sealed source")
    if not output.resolve().is_relative_to((ROOT / "qa-private").resolve()):
        raise ValueError("Raw data belongs only in qa-private")
    if output.exists():
        raw = output.read_bytes()
    else:
        with urllib.request.urlopen(expected, timeout=45) as response:
            raw = response.read(manifest["bytes"] + 1)
    if len(raw) != manifest["bytes"] or hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Unexpected dataset bytes")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as target:
            target.write(raw)
    return {key: manifest[key] for key in ("rows", "sha256", "revision")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qa-private/pcr-test.json")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch(args.output)))
    except (OSError, ValueError, KeyError):
        print("Sealed PCR dataset unavailable or changed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
