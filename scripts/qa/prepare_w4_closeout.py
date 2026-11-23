"""Create a fresh five-service W4 project with random synthetic-test credentials."""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/qa/w4_new40"))
from common import BASE_COMMIT, RUN_DIRECTORY  # noqa: E402
from run_owned import prepare  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    assert args.project.startswith("ouc-w4-new40-")
    assert not subprocess.check_output(["git", "diff", "HEAD", "--", "services", "infra", "apps",
                                        "packages/contract"], cwd=ROOT)
    suite = prepare(args.project)
    suite.command("up", "-d", "--build", "--wait", "--wait-timeout", "240")
    provenance = dict(source_commit=BASE_COMMIT, built_at_utc=datetime.now(UTC).isoformat(),
                      project=suite.project, build="Current clean checkout via Dockerfiles",
                      image_observations=suite.command("images", "--format", "json"),
                      fresh_volumes=True, synthetic_identity_provider=True,
                      live_wechat_acceptance=False)
    (ROOT / RUN_DIRECTORY / "image-provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": suite.project, "healthy": True, "source": BASE_COMMIT}))


if __name__ == "__main__":
    main()
