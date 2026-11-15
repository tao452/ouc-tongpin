"""Fetch a pinned, independently labeled test split into the ignored private directory."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/qa/data/external/cold-test.v1.json"


def fetch(output, opener=urllib.request.urlopen):
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
    if output.exists():
        raw = output.read_bytes()
    else:
        request = urllib.request.Request(expected, headers={"User-Agent": "ouc-tongpin-qa"})
        with opener(request, timeout=45) as response:
            raw = response.read(manifest["bytes"] + 1)
    if len(raw) != manifest["bytes"] or hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Unexpected external corpus bytes")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as target:
                temporary = Path(target.name)
                target.write(raw)
            os.replace(temporary, output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {"dataset": manifest["name"], "bytes": len(raw), "sha256": manifest["sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qa-private/cold-test.csv")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch(args.output)))
    except (OSError, ValueError, TypeError, KeyError):
        print("Download failed: invalid metadata, cache or upstream response", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
