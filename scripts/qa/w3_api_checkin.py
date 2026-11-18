"""Fourteen independent check-in contracts on per-run synthetic future dates."""

import concurrent.futures
import hashlib
import json
import urllib.parse
from datetime import timedelta

from regression_http import Client, expect


def register(runner, stack, start_date):
    client = runner.client
    route = "/api/emotions/checkins"

    def payload(offset, changes=None, remove=()):
        result = {"emotion": "HAPPY", "intensity": 3,
                  "checkinDate": (start_date + timedelta(days=offset)).isoformat()}
        result.update(changes or {})
        for key in remove:
            result.pop(key, None)
        return result

    def submit(data, expected=200):
        before = stack.count("checkin")
        status, body = client.request(route, data)
        expect(status == expected, f"Expected HTTP {expected}, received {status}")
        after = stack.count("checkin")
        if expected == 200:
            expect(after == before + 1, "Successful new date must persist exactly one row")
            expect(isinstance(body, dict), "Successful check-in must return an object")
            for field in ("emotion", "intensity", "checkinDate", "note"):
                if field in data:
                    expect(body.get(field) == data[field], "Submitted field differs: " + field)
            identifier = int(body["id"])
            persisted = stack.sql(
                "SELECT emotion,intensity,checkin_date,SHA2(COALESCE(note,''),256),user_id "
                f"FROM checkin WHERE id={identifier}"
            ).split("\t")
            expected_row = [data["emotion"], str(data["intensity"]), data["checkinDate"],
                            hashlib.sha256(data.get("note", "").encode()).hexdigest(),
                            str(client.user_id)]
            expect(persisted == expected_row,
                   "MySQL check-in fields must match submitted values and authenticated caller")
        else:
            expect(after == before, "Rejected check-in must not change persisted data")
        client.observations.append({"database_rows_added": after - before})
        return body

    def emotions():
        for offset, emotion in enumerate(
            ("HAPPY", "CALM", "ANXIOUS", "LONELY", "IRRITABLE", "DOWN"), 1
        ):
            submit(payload(offset, {"emotion": emotion}))

    runner.run("W3-CHECKIN-01", emotions)
    for identifier, offset, intensity, status in (
        ("02", 11, 1, 200), ("03", 12, 5, 200),
        ("04", 13, 0, 400), ("05", 14, 6, 400),
    ):
        runner.run("W3-CHECKIN-" + identifier,
                   lambda o=offset, v=intensity, s=status:
                   submit(payload(o, {"intensity": v}), s))
    runner.run("W3-CHECKIN-06",
               lambda: submit(payload(15, {"emotion": "UNKNOWN"}), 400))
    runner.run("W3-CHECKIN-07",
               lambda: submit(payload(16, remove=("emotion",)), 400))
    runner.run("W3-CHECKIN-08",
               lambda: submit(payload(17, remove=("intensity",)), 400))
    runner.run("W3-CHECKIN-09", lambda: submit(payload(18, {"note": "好" * 100})))
    runner.run("W3-CHECKIN-10", lambda: submit(payload(19, {"note": "好" * 101}), 400))

    def repeat():
        data = payload(20)
        first = submit(data)
        before = stack.count("checkin")
        status, second = client.request(route, data)
        expect(status == 200 and second == first, "Repeat must return the original record")
        expect(stack.count("checkin") == before, "Repeat must not insert a second row")
        client.observations.append({"repeat_database_rows_added": 0})

    runner.run("W3-CHECKIN-11", repeat)

    def interval():
        seeded = [submit(payload(offset)) for offset in (30, 31, 32)]
        query = urllib.parse.urlencode({"from": seeded[0]["checkinDate"],
                                       "to": seeded[-1]["checkinDate"]})
        status, body = client.request(route + "?" + query)
        expect(status == 200 and body["total"] == 3, "Inclusive range must contain three rows")
        expect(len(body["items"]) == 3, "Range total must equal returned item count")
        expect({item["id"] for item in body["items"]} == {item["id"] for item in seeded},
               "Date range must return exactly its seeded records")

    runner.run("W3-CHECKIN-12", interval)

    def invalid_dates():
        before = stack.count("checkin")
        start = start_date.isoformat()
        end = (start_date + timedelta(days=1)).isoformat()
        for query in ("from=W3-PRIVATE-INVALID-DATE", f"from={end}&to={start}"):
            status, body = client.request(route + "?" + query)
            expect(status == 400, "Invalid or reversed date range must return 400")
            expect("W3-PRIVATE-INVALID-DATE" not in json.dumps(body), "Error must not echo input")
        expect(stack.count("checkin") == before, "Invalid query must not mutate MySQL")
        client.observations.append({"database_rows_added": 0})

    runner.run("W3-CHECKIN-13", invalid_dates)

    def concurrent_submissions():
        data = payload(40, {"emotion": "CALM"})
        before = stack.count("checkin")

        def request(_):
            other = Client(client.base, token=client.token, user_id=client.user_id)
            status, body = other.request(route, data)
            return status, body, other.observations

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(request, range(8)))
        for _, _, observations in replies:
            client.observations.extend(observations)
        expect(all(status == 200 for status, _, _ in replies), "Concurrent request failed")
        expect(len({body["id"] for _, body, _ in replies}) == 1,
               "Concurrent requests must return the same record ID")
        expect(stack.count("checkin") == before + 1, "Concurrent requests must insert one row")
        client.observations.append({"concurrent_requests": 8, "distinct_record_ids": 1,
                                    "database_rows_added": 1})

    runner.run("W3-CHECKIN-14", concurrent_submissions)
