import hashlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/qa"))
from dataset_cache import load_pinned  # noqa: E402


def test_download_cache_offline_fallback_and_tamper(tmp_path):
    raw = b"synthetic sealed bytes"
    manifest = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "url": "https://example.invalid/pinned"}
    output = tmp_path / "corpus"
    result = load_pinned(output, manifest, lambda *a, **k: io.BytesIO(raw))
    assert result["source"] == "pinned-download"

    def offline(*args, **kwargs):
        raise OSError("offline")

    assert load_pinned(output, manifest, offline)["source"] == "verified-cache"
    assert load_pinned(output, manifest, offline, True)["source"].endswith("network-failure")
    with pytest.raises(ValueError, match="Downloaded"):
        load_pinned(output, manifest, lambda *a, **k: io.BytesIO(b"bad"), True)
    assert output.read_bytes() == raw
    output.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Cached"):
        load_pinned(output, manifest, offline)
    output.unlink()
    with pytest.raises(OSError, match="First download failed"):
        load_pinned(output, manifest, offline)
    assert not output.exists()
