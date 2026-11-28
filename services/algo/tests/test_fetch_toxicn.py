import hashlib
import importlib.util
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("fetch_toxicn", ROOT / "scripts/qa/fetch_toxicn.py")
acquire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquire)


@pytest.fixture
def pinned(tmp_path, monkeypatch):
    data = b"content,toxic\nsynthetic,0\n"
    monkeypatch.setattr(acquire, "ROOT", tmp_path)
    monkeypatch.setattr(acquire, "SIZE", len(data))
    monkeypatch.setattr(acquire, "BLOB", hashlib.sha1(
        f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest())
    return tmp_path / "qa-private/source.csv", data


def test_pinned_fetch_uses_author_mirror_after_network_failure_and_verifies_cache(pinned):
    path, data = pinned
    calls = []

    def opener(url, timeout):
        calls.append(url)
        assert timeout == 45
        if len(calls) == 1:
            raise OSError("temporary network failure")
        return io.BytesIO(data)

    result = acquire.fetch(path, opener)
    assert calls == [acquire.URL, acquire.MIRROR]
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert acquire.fetch(path, lambda *a, **kw: pytest.fail("cache should avoid network")) == result


def test_damaged_cache_and_changed_remote_bytes_are_not_accepted_or_overwritten(pinned):
    path, _ = pinned
    with pytest.raises(ValueError, match="differs"):
        acquire.fetch(path, lambda *a, **kw: io.BytesIO(b"bad"))
    assert not path.exists()
    path.parent.mkdir(parents=True)
    path.write_bytes(b"damaged cache")
    with pytest.raises(ValueError, match="differs"):
        acquire.fetch(path)
    assert path.read_bytes() == b"damaged cache"


def test_raw_corpus_cannot_be_written_into_public_docs(pinned):
    path, _ = pinned
    with pytest.raises(ValueError, match="qa-private"):
        acquire.fetch(path.parent.parent / "docs/source.csv")
