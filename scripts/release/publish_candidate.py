"""Publish only an existing version tag with successful CI and verified candidate checksums."""
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from package_candidate import digest, verify


def main():
    ref = os.environ.get("GITHUB_REF", "")
    if not re.fullmatch(r"refs/tags/v\d+\.\d+\.\d+", ref):
        raise SystemExit("Select an existing vX.Y.Z tag for publication")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise SystemExit("Publication requires a manual workflow dispatch")
    folder = Path("qa-private/release-candidate")
    manifest = verify(folder)
    for row in (folder / "SHA256SUMS").read_text().splitlines():
        expected, name = row.split("  ", 1)
        if Path(name).name != name or digest(folder / name) != expected:
            raise SystemExit("Candidate checksum mismatch")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if manifest["source_commit"] != sha:
        raise SystemExit("Candidate does not match selected tag")
    main_sha = subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip()
    if sha != main_sha:
        raise SystemExit("Publication tag must point to the current main commit")
    repo = os.environ["GITHUB_REPOSITORY"]
    headers = {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
               "User-Agent": "ouc-tongpin-release", "Content-Type": "application/json"}
    base = "https://api.github.com/repos/" + repo

    def request(url, payload=None, method=None, content_type="application/json"):
        data = payload if isinstance(payload, bytes) else (
            json.dumps(payload).encode() if payload is not None else None)
        req = urllib.request.Request(url, data=data,
                                     headers={**headers, "Content-Type": content_type},
                                     method=method)
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)

    checks = request(base + "/commits/" + sha +
                     "/check-runs?check_name=quality&filter=latest&per_page=100")["check_runs"]
    latest = max(checks, key=lambda c: c["id"]) if checks else None
    if latest is None or latest["conclusion"] != "success":
        raise SystemExit("Selected commit needs a successful quality check")
    release = request(base + "/releases", {"tag_name": ref.removeprefix("refs/tags/"),
                       "name": ref.removeprefix("refs/tags/"), "draft": True,
                       "body": "Source commit: " + sha + "\nChecksums: SHA256SUMS"})
    upload = release["upload_url"].split("{", 1)[0]
    for path in sorted(folder.iterdir()):
        if path.is_file():
            request(upload + "?name=" + urllib.parse.quote(path.name), path.read_bytes(),
                    "POST", "application/octet-stream")
    release = request(base + "/releases/" + str(release["id"]), {"draft": False}, "PATCH")
    print("Published", release["html_url"])


if __name__ == "__main__":
    main()
