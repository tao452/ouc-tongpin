"""Pinned private dataset cache; offline runs never need a network refresh."""

import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from http.client import HTTPException
from pathlib import Path


def load_pinned(output, manifest, opener=urllib.request.urlopen, refresh=False):
    def valid(raw):
        return (len(raw) == manifest["bytes"]
                and hashlib.sha256(raw).hexdigest() == manifest["sha256"])

    cached = output.read_bytes() if output.exists() else None
    if cached is not None and not valid(cached):
        raise ValueError("Cached dataset SHA256 mismatch; retain it for inspection")
    if cached is not None and not refresh:
        return {"source": "verified-cache", "sha256": manifest["sha256"]}
    request = urllib.request.Request(manifest["url"], headers={"User-Agent": "ouc-tongpin-qa"})
    raw = None
    for _ in range(2):
        try:
            with opener(request, timeout=20) as response:
                raw = response.read(manifest["bytes"] + 1)
            break
        except (OSError, urllib.error.URLError, HTTPException):
            continue
    if raw is None:
        if cached is not None:
            return {"source": "verified-cache-after-network-failure", "sha256": manifest["sha256"]}
        raise OSError("First download failed; no verified local dataset cache is available")
    if not valid(raw):
        raise ValueError("Downloaded dataset SHA256/size mismatch; cache was not replaced")
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
    return {"source": "pinned-download", "sha256": manifest["sha256"]}
