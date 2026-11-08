import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "candidate", ROOT / "scripts/release/package_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def fixture(folder, extra=None):
    names = ["infra/docker-compose.yml", "services/algo/Dockerfile",
             "services/api-server/Dockerfile"]
    if extra:
        names.append(extra)
    with tarfile.open(folder / "deployment-source.tar.gz", "w:gz") as archive:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = 1
            archive.addfile(info, io.BytesIO(b"x"))
    (folder / "api-server.jar").write_bytes(b"synthetic fixture, not a built release")
    (folder / "admin-web.tar.gz").write_bytes(b"synthetic fixture")
    manifest = {"format_version": 1, "files": [
        {"name": name, "bytes": (folder / name).stat().st_size,
         "sha256": candidate.digest(folder / name)} for name in (
             "deployment-source.tar.gz", "api-server.jar", "admin-web.tar.gz")]}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_candidate_checksums_and_tamper_detection(tmp_path):
    fixture(tmp_path)
    assert candidate.verify(tmp_path)["format_version"] == 1
    (tmp_path / "api-server.jar").write_bytes(b"modified")
    with pytest.raises(ValueError, match="checksum"):
        candidate.verify(tmp_path)


@pytest.mark.parametrize("path", [
    ".env", "qa-private/records.json", "../outside", "/outside", "C:/outside"])
def test_candidate_rejects_private_or_unsafe_source_archive(tmp_path, path):
    fixture(tmp_path, path)
    with pytest.raises(ValueError):
        candidate.verify(tmp_path)


def test_publishing_requires_manual_version_tag():
    env = {**os.environ, "GITHUB_REF": "refs/heads/test", "GITHUB_EVENT_NAME": "pull_request"}
    result = subprocess.run([sys.executable, str(ROOT / "scripts/release/publish_candidate.py")],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "existing vX.Y.Z tag" in result.stderr
