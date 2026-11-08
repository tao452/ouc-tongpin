"""Build a checksum-verified deployment source bundle and compiled Java/frontend assets."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(folder):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["format_version"] == 1, "Unsupported manifest version")
    expected = {"deployment-source.tar.gz", "api-server.jar", "admin-web.tar.gz"}
    require(len(manifest["files"]) == 3 and {
        item["name"] for item in manifest["files"]} == expected, "Invalid candidate files")
    for item in manifest["files"]:
        path = folder / item["name"]
        require(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"],
                "Candidate checksum mismatch")
    with tarfile.open(folder / "deployment-source.tar.gz") as archive:
        names = set(archive.getnames())
        for entry in archive.getmembers():
            name = entry.name
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in name
                    and not PureWindowsPath(name).drive, "Unsafe archive path")
            require(entry.isfile() or entry.isdir(), "Unsupported archive entry")
            require(".env" not in path.parts and "qa-private" not in path.parts,
                    "Private data in archive")
        require({"infra/docker-compose.yml", "services/algo/Dockerfile",
                 "services/api-server/Dockerfile"} <= names, "Deployment sources missing")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    folder = args.output
    if args.verify_only:
        print("Verified candidate", verify(folder)["source_commit"])
        return
    folder.mkdir(parents=True, exist_ok=False)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "archive", "--format=tar.gz", "-o",
                    str((folder / "deployment-source.tar.gz").resolve()), "HEAD"], check=True)
    shutil.copyfile("services/api-server/target/api-server-0.1.0.jar", folder / "api-server.jar")
    with tarfile.open(folder / "admin-web.tar.gz", "w:gz") as archive:
        archive.add("apps/admin-web/dist", arcname="admin-web")
    files = [{"name": name, "bytes": (folder / name).stat().st_size,
              "sha256": digest(folder / name)}
             for name in ("deployment-source.tar.gz", "api-server.jar", "admin-web.tar.gz")]
    manifest = {"format_version": 1, "source_commit": source,
                "created_at_utc": datetime.now(UTC).isoformat(),
                "runtime": {"java": "17", "python": "3.11", "node": "22"}, "files": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    (folder / "SHA256SUMS").write_text("\n".join(
        f"{digest(path)}  {path.name}" for path in sorted(folder.iterdir()) if path.is_file()
    )+"\n", encoding="utf-8")
    verify(folder)
    print(json.dumps({"source_commit": source, "files": files}))


if __name__ == "__main__":
    main()
