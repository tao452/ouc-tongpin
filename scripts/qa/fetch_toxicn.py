"""Fetch pinned ToxiCN data for local evaluation; never commit the source text."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = "91d8f6a449967bd310364544d535d6310e45043b"
BLOB = "37405e18a964b65d49a1ae83b2dee66989059112"
SIZE = 2318453
URL = f"https://raw.githubusercontent.com/DUT-lujunyu/ToxiCN/{REVISION}/ToxiCN_1.0.csv"
MIRROR = ("https://huggingface.co/datasets/JunyuLu/ToxiCN/resolve/"
          "86d8f868cdb89ffaf4f1daea0cf75bd0e1b2f7cf/ToxiCN_1.0.csv")


def fetch(output, opener=urllib.request.urlopen):
    if not output.resolve().is_relative_to((ROOT / "qa-private").resolve()):
        raise ValueError("Raw external text belongs only in qa-private")
    if output.exists():
        raw = output.read_bytes()
    else:
        raw = b""
        for url in (URL, MIRROR):
            try:
                with opener(url, timeout=45) as response:
                    chunks, size = [], 0
                    while size < SIZE:
                        chunk = response.read(min(65536, SIZE - size))
                        if not chunk:
                            break
                        size += len(chunk)
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                if len(raw) == SIZE:
                    break
            except OSError:
                continue
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw, usedforsecurity=False).hexdigest()
    if len(raw) != SIZE or blob != BLOB:
        raise ValueError("Pinned source differs")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        with output.open("xb") as handle:
            handle.write(raw)
    return {"revision": REVISION, "git_blob": BLOB, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch(args.output)))
    except (OSError, ValueError):
        print("Pinned ToxiCN acquisition failed")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
