"""Execute catalogue cases against isolated local processes; preserve failures in JSON."""
import argparse
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


def execute(api, algo):
    results = []
    observations = []

    def request(base, path, payload=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None)
        req = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status, content = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, content = error.code, error.read()
        try:
            body = json.loads(content)
        except ValueError:
            body = None
        summary = {"http_status": status}
        if isinstance(body, dict):
            for key in ("passed", "emotion", "intensity", "checkinDate", "total"):
                if key in body:
                    summary[key] = body[key]
            if "hits" in body:
                summary["hit_levels"] = [hit["level"] for hit in body["hits"]]
        observations.append(summary)
        return status, body

    def run(number, check):
        observations.clear()
        try:
            check()
            status, reason = "PASS", None
        except AssertionError as error:
            status, reason = "FAIL", str(error) or "Observed response differs from catalogue"
        except OSError:
            status, reason = "BLOCKED", "Test service unreachable"
        results.append({"case_id": f"S1-{number:03d}", "status": status,
                        "observations": list(observations), "reason": reason})

    def moderation(text, expected_passed, level=None, expected_status=200):
        status, body = request(algo, "/api/moderation/check", {"text": text})
        assert status == expected_status, f"Expected HTTP {expected_status}, received {status}"
        if status == 200:
            assert body["passed"] is expected_passed
            if level:
                assert any(hit["level"] == level for hit in body["hits"])
            else:
                assert body["hits"] == []

    run(55, lambda: moderation("一起去图书馆", True))
    run(56, lambda: moderation("傻逼", False, "HIGH"))
    # Policy checks are observed but await M1's acceptance of the level/action mapping.
    for number, text, level in ((57, "废物", "MEDIUM"), (58, "垃圾", "LOW")):
        run(number, lambda text=text, level=level: moderation(text, True, level))
        if results[-1]["status"] == "PASS":
            results[-1].update(status="BLOCKED",
                               reason="Level/action policy pending M1 confirmation")

    def traditional():
        left = request(algo, "/api/moderation/check", {"text": "操你媽"})
        right = request(algo, "/api/moderation/check", {"text": "操你妈"})
        assert left == right and left[0] == 200 and left[1]["passed"] is False

    run(59, traditional)
    run(60, lambda: moderation("ＳＨＡＢＩ", False, "HIGH"))
    run(61, lambda: moderation("煞笔", False, "HIGH"))

    def pinyin():
        moderation("shabi", False, "HIGH")
        moderation("shabilist", True)

    run(62, pinyin)
    run(63, lambda: moderation("傻*\u200b逼", False, "HIGH"))
    run(64, lambda: moderation(" ", None, expected_status=422))
    run(65, lambda: moderation("好" * 2000, True))
    run(66, lambda: moderation("好" * 2001, None, expected_status=422))

    def malformed():
        status, body = request(algo, "/api/moderation/check", raw=b"{")
        assert status == 422 and body == {"detail": "Invalid request"}

    run(67, malformed)

    def oversized():
        status, _ = request(algo, "/api/moderation/check", raw=b"x" * 16385)
        assert status == 413

    run(68, oversized)
    if results[-1]["status"] == "PASS":
        results[-1].update(status="BLOCKED",
                           reason="Direct service passed; gateway check pending CI")

    def checkin(number, changes=None, remove=(), expected_status=200):
        payload = {"emotion": "HAPPY", "intensity": 3,
                   "checkinDate": (date(2030, 1, 1) + timedelta(days=number)).isoformat()}
        payload.update(changes or {})
        for key in remove:
            del payload[key]
        before = request(api, "/api/emotions/checkins")[1]["total"]
        status, body = request(api, "/api/emotions/checkins", payload)
        assert status == expected_status, f"Expected HTTP {expected_status}, received {status}"
        if status == 200:
            assert body["emotion"] == payload["emotion"]
            assert body["intensity"] == payload["intensity"]
            if "note" in payload:
                assert body["note"] == payload["note"]
            if "checkinDate" in payload:
                assert body["checkinDate"] == payload["checkinDate"]
        else:
            assert request(api, "/api/emotions/checkins")[1]["total"] == before
        return payload, body

    emotions = ("HAPPY", "CALM", "ANXIOUS", "LONELY", "IRRITABLE", "DOWN")
    for number, emotion in enumerate(emotions, 13):
        run(number, lambda number=number, emotion=emotion: checkin(number, {"emotion": emotion}))
    for number, value, status in ((19, 1, 200), (20, 5, 200), (21, 0, 400), (22, 6, 400)):
        run(number, lambda number=number, value=value, status=status:
            checkin(number, {"intensity": value}, expected_status=status))
    run(23, lambda: checkin(23, {"emotion": "UNKNOWN"}, expected_status=400))

    def missing_fields():
        checkin(24, remove=("emotion",), expected_status=400)
        checkin(24, remove=("intensity",), expected_status=400)

    run(24, missing_fields)
    run(25, lambda: checkin(25, {"note": "好" * 100}))
    run(26, lambda: checkin(26, {"note": "好" * 101}, expected_status=400))

    def idempotent():
        payload, first = checkin(27)
        count = request(api, "/api/emotions/checkins")[1]["total"]
        second = request(api, "/api/emotions/checkins", payload)
        assert second == (200, first)
        assert request(api, "/api/emotions/checkins")[1]["total"] == count

    run(27, idempotent)

    def today():
        before = date.today().isoformat()
        _, result = checkin(28, remove=("checkinDate",))
        assert result["checkinDate"] in {before, date.today().isoformat()}

    run(28, today)

    def date_range():
        start, end = "2030-01-14", "2030-01-20"
        query = urllib.parse.urlencode({"from": start, "to": end})
        status, body = request(api, "/api/emotions/checkins?" + query)
        assert status == 200 and body["total"] == len(body["items"])
        assert body["total"] > 0
        assert all(start <= item["checkinDate"] <= end for item in body["items"])

    run(29, date_range)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--algo-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = execute(args.api_url, args.algo_url)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report = {"executed_at_utc": datetime.now(UTC).isoformat(), "source_commit": source,
              "scope": "Isolated processes, five-word dictionary; Java demoUser memory store, "
                       "no authentication, database persistence or formal policy acceptance.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(content, encoding="utf-8")
    print(json.dumps({status: sum(r["status"] == status for r in results)
                      for status in ("PASS", "FAIL", "BLOCKED")}))
    return int(any(r["status"] == "FAIL" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
