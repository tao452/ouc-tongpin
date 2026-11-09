"""Existing check-in contract, persistence and concurrent idempotency regression."""

import concurrent.futures
import json
import urllib.parse
from datetime import date, timedelta

from regression_http import Client, expect


def register(runner, stack):
    client = runner.client
    route = "/api/emotions/checkins"

    def check(number, changes=None, remove=(), expected=200):
        payload = {
            "emotion": "HAPPY",
            "intensity": 3,
            "checkinDate": (date(2031, 1, 1) + timedelta(days=number)).isoformat(),
        }
        payload.update(changes or {})
        for key in remove:
            payload.pop(key, None)
        before = stack.count("checkin")
        status, body = client.request(route, payload)
        expect(status == expected, f"Expected HTTP {expected}, received {status}")
        after = stack.count("checkin")
        client.observations.append({"database_rows_before": before, "database_rows_after": after})
        if expected == 200:
            expect(body["emotion"] == payload["emotion"], "Emotion differs from submitted value")
            expect(body["intensity"] == payload["intensity"], "Intensity differs")
            expect(after == before + 1, "Successful check-in must persist exactly once")
            if "checkinDate" in payload:
                expect(body["checkinDate"] == payload["checkinDate"], "Date differs")
            if "note" in payload:
                expect(body["note"] == payload["note"], "Note differs")
        else:
            expect(after == before, "Rejected input changed persisted data")
        return payload, body

    for number, emotion in enumerate(
        ("HAPPY", "CALM", "ANXIOUS", "LONELY", "IRRITABLE", "DOWN"), 13
    ):
        runner.run(f"S1-{number:03}", lambda n=number, e=emotion: check(n, {"emotion": e}))
    for number, value, expected in ((19, 1, 200), (20, 5, 200), (21, 0, 400), (22, 6, 400)):
        runner.run(
            f"S1-{number:03}",
            lambda n=number, v=value, s=expected: check(n, {"intensity": v}, expected=s),
        )
    runner.run("S1-023", lambda: check(23, {"emotion": "UNKNOWN"}, expected=400))

    def missing():
        check(24, remove=("emotion",), expected=400)
        check(24, remove=("intensity",), expected=400)

    runner.run("S1-024", missing)
    runner.run("S1-025", lambda: check(25, {"note": "好" * 100}))
    runner.run("S1-026", lambda: check(26, {"note": "好" * 101}, expected=400))

    def repeated():
        payload, first = check(27)
        before = stack.count("checkin")
        status, second = client.request(route, payload)
        expect(status == 200 and second == first, "Repeat must return the original record")
        expect(stack.count("checkin") == before, "Repeat inserted another row")

    runner.run("S1-027", repeated)

    def today():
        before_date = stack.execute("exec", "-T", "api", "date", "+%F")
        _, body = check(28, remove=("checkinDate",))
        after_date = stack.execute("exec", "-T", "api", "date", "+%F")
        expect(body["checkinDate"] in {before_date, after_date}, "Default differs from server date")
        expect(
            stack.sql("SELECT checkin_date FROM checkin WHERE id=" + str(int(body["id"])))
            == body["checkinDate"],
            "Returned date was not persisted",
        )

    runner.run("S1-028", today)

    def interval():
        query = urllib.parse.urlencode({"from": "2031-01-14", "to": "2031-01-20"})
        status, body = client.request(route + "?" + query)
        expect(status == 200 and body["total"] == 7, "Inclusive date range must contain seven rows")
        expect(len(body["items"]) == 7, "Total differs from returned items")
        expect(
            all("2031-01-14" <= row["checkinDate"] <= "2031-01-20" for row in body["items"]),
            "Date filter leaked out-of-range rows",
        )

    runner.run("S1-029", interval)

    def invalid_dates():
        before = stack.count("checkin")
        for query in ("from=private-invalid-date", "from=2031-02-02&to=2031-01-01"):
            status, body = client.request(route + "?" + query)
            expect(status == 400, "Invalid query dates must return 400")
            expect("private-invalid-date" not in json.dumps(body), "Error echoed request input")
        expect(stack.count("checkin") == before, "Invalid query mutated data")

    runner.run("API-CHECKIN-DATES", invalid_dates)

    def concurrent_submissions():
        payload = {"emotion": "CALM", "intensity": 3, "checkinDate": "2032-01-01"}
        before = stack.count("checkin")

        def submit(_):
            return Client(client.base).request(route, payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(submit, range(8)))
        expect(all(status == 200 for status, _ in replies), "Concurrent submission failed")
        expect(
            len({body["id"] for _, body in replies}) == 1,
            "Concurrent requests returned different IDs",
        )
        expect(stack.count("checkin") == before + 1, "Concurrent requests inserted duplicate rows")
        client.observations.append(
            {"concurrent_requests": 8, "distinct_record_ids": 1, "database_rows_added": 1}
        )

    runner.run("API-CHECKIN-CONCURRENT", concurrent_submissions)
