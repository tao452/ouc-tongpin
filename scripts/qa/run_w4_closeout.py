"""Re-run 120 catalogue cases on an existing fresh, owned W4 stack; keep all evidence."""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/qa/w4_new40"))
import run_existing_api_regression as old80  # noqa: E402
import run_us25_security as privacy  # noqa: E402
from assemble import assemble  # noqa: E402
from collect_java_evidence import collect  # noqa: E402
from common import BASE_COMMIT, RUN_DIRECTORY, Suite  # noqa: E402
from regression_http import Client, expect  # noqa: E402
from regression_stack import Stack  # noqa: E402
from run_owned import java  # noqa: E402
from us25_privacy_runtime import PrivacyStack  # noqa: E402


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_cases(s):
    results = []
    actor = s.actor()

    def run(cid, check):
        s.trace = []
        try:
            check()
            status, reason = "PASS", None
        except AssertionError as error:
            status, reason = "FAIL", str(error)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            status, reason = "BLOCKED", type(error).__name__
        results.append(dict(case_id=cid, status=status, reason=reason, evidence=list(s.trace)))

    def query(lat, lng, radius=5000, size=10):
        return s.http("/api/match/needs/square", dict(myLatitude=lat, myLongitude=lng,
                      radius=radius, size=size), actor["token"])

    def edges():
        for lat, lng in [(-90, 0), (90, 0), (0, -180), (0, 180)]:
            assert query(lat, lng)[0] == 200

    def invalid():
        before = s.sql("SELECT COUNT(*) FROM buddy_demand")
        cache = s.redis("KEYS", "square:*")
        for lat, lng in [(-90.000001, 0), (90.000001, 0), (0, -180.000001), (0, 180.000001)]:
            assert query(lat, lng)[0] == 400
        assert s.sql("SELECT COUNT(*) FROM buddy_demand") == before
        assert s.redis("KEYS", "square:*") == cache

    def cache_scope():
        ids = []
        for lat, lng in [(0, 0), (0.1, 0), (0, 1), (0, -180)]:
            body = s.need()
            body["location"].update(lat=lat, lng=lng)
            status, value, _ = s.buddy(actor, body)
            assert status == 201
            ids.append(str(value["id"]))

        def found(lat, lng, radius=4099, size=9):
            status, body, _ = query(lat, lng, radius, size)
            assert status == 200
            return {row["id"] for row in body["data"]}

        assert ids[0] in found(0, 0)
        assert ids[1] not in found(0, 0)
        assert {ids[0], ids[1]} <= found(0, 0, 20000)
        assert ids[2] in found(0, 1)
        assert ids[0] not in found(0, 1)
        assert len(found(0, 0, 20000, 1)) == 1
        assert ids[3] in found(0, -180)
        assert ids[3] in found(0, 180)

    run("W4-QRY-01", edges)
    run("W4-QRY-02", invalid)
    run("W4-QRY-03", cache_scope)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    assert args.project.startswith("ouc-w4-new40-")
    folder = ROOT / RUN_DIRECTORY
    s = Suite(args.project, folder / "http-results.json")
    s.require_empty()
    # Capture regular JUnit results before the opt-in database IT adds its XML.
    regular = collect(ROOT / "services/api-server/target/surefire-reports")
    save(folder / "regular-java.json", regular)
    subprocess.run([sys.executable, str(ROOT / "scripts/qa/w4_new40/run_http.py"),
                    "--project", s.project, "--output", str(s.output)], cwd=ROOT, check=True)
    java_exit = java(s, folder)
    current40 = assemble(s.output, None, ROOT / "services/api-server/target/surefire-reports/"
                         "TEST-com.ouctongpin.apiserver.w4.W4DatabaseCasesIT.xml",
                         folder / "java-events", folder / "new40.json")
    Stack.command = tuple(s.compose)
    PrivacyStack.command = tuple(s.compose)
    if os.environ.get("W4_NATIVE_STORAGE") == "true":
        Stack.sql = lambda self, statement: s.sql(statement)
        Stack.redis = lambda self, *arguments: s.redis(*arguments)
    original = old80.execute("http://127.0.0.1:" + str(s.base))
    save(folder / "original80-http.json", dict(source_commit=BASE_COMMIT, results=original))
    results = [row for row in original if row["case_id"].startswith("S1-")]
    client = Client("http://127.0.0.1:" + str(s.base)).authenticate()
    stack_rows = []
    for number, action in [
        (77, lambda: s.command("config", "-q")),
        (78, lambda: s.command("ps", "--format", "json")),
        (79, lambda: subprocess.check_output([sys.executable, "scripts/e2e/foundation-smoke.py"],
              cwd=ROOT, env={**os.environ, "TEST_BASE_URL": client.base}, text=True)),
    ]:
        try:
            observed = action()
            if number == 78:
                services = [json.loads(line) for line in observed.splitlines() if line.strip()]
                expect(len(services) == 5 and all(r["Health"] == "healthy" for r in services),
                       "All five services must be healthy")
            stack_rows.append(dict(case_id=f"S1-{number:03}", status="PASS",
                                   observations=[{"checked": True, "output": observed}]))
        except (AssertionError, OSError, subprocess.SubprocessError) as error:
            stack_rows.append(dict(case_id=f"S1-{number:03}", status="FAIL",
                                   observations=[], reason=type(error).__name__))
    # config -q has no output; no environment values are retained.
    results += regular["catalogue_results"] + stack_rows
    diagnostics = {}
    security, pii = privacy.execute(client.base, s.env, diagnostics)
    save(folder / "privacy.json", dict(source_commit=BASE_COMMIT, results=security,
         runtime_pii_scan=pii, independent_reproduction="PENDING", live_wechat=False))
    save(folder / "query.json", dict(source_commit=BASE_COMMIT, results=query_cases(s)))
    all_rows = sorted(results + current40["results"], key=lambda row: row["case_id"])
    assert len(all_rows) == 120 and len({row["case_id"] for row in all_rows}) == 120
    counts = dict(Counter(row["status"] for row in all_rows))
    save(folder / "all120.json", dict(source_commit=BASE_COMMIT,
         executed_at_utc=datetime.now(UTC).isoformat(), results=all_rows, status_counts=counts,
         pass_rate=counts.get("PASS", 0) / 120, denominator=120, java_integration_exit=java_exit,
         scope="Owned MySQL8/Redis/HTTP; synthetic WeChat identity; author execution"))
    print(json.dumps({"120": counts, "40": current40["status_counts"]}))
    return int(java_exit != 0 or counts.get("FAIL", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
