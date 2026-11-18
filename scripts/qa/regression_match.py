"""US-10 publishing catalogue cases S1-047..054 against the real endpoint.

Replaces the former "endpoint is not implemented" BLOCKED placeholders.
Every accepted case asserts exactly one new buddy_demand row; every rejected
case asserts no row was written.
"""

from regression_http import expect

ROUTE = "/api/match/needs"
MISSING = object()

VALID = {
    "scene": "自习",
    "time": "2026-11-15T10:00:00+08:00",
    "location": {"address": "图书馆", "lat": 36.16, "lng": 120.4},
    "skillTags": ["高数"],
    "remark": "一起复习",
}


def payload(**changes):
    body = dict(VALID)
    for key, value in changes.items():
        if value is MISSING:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def register(runner, stack):
    client = runner.client

    def submit(**changes):
        body = payload(**changes)
        status, response = client.request(ROUTE, body)
        return status, response, body

    def accepted(**changes):
        before = stack.count("buddy_demand")
        status, response, body = submit(**changes)
        expect(status == 201, f"Expected HTTP 201, received {status}")
        expect(isinstance(response, dict), "201 response must be a JSON object")
        expect(
            set(response) == {"id", "scene", "status"},
            "201 response fields differ from the contract",
        )
        expect(
            isinstance(response["id"], str) and response["id"].isdigit(),
            "id must be a string per the contract",
        )
        expect(response["scene"] == body["scene"], "scene was changed")
        expect(response["status"] == "OPEN", "status must be OPEN")
        expect(
            not ({"userId", "user_id", "anonymousId", "openid", "studentNo", "phone"}
                 & response.keys()),
            "Response exposed internal identity fields",
        )
        expect(stack.count("buddy_demand") == before + 1, "Publication must add one row")

    def rejected(**changes):
        before = stack.count("buddy_demand")
        status, _, _ = submit(**changes)
        expect(status == 400, f"Expected HTTP 400, received {status}")
        expect(stack.count("buddy_demand") == before, "Rejected request must not create a row")

    runner.run("S1-047", lambda: accepted())
    runner.run("S1-048", lambda: rejected(scene=MISSING))
    runner.run("S1-049", lambda: rejected(time=MISSING))
    runner.run("S1-050", lambda: rejected(location=MISSING))
    runner.run("S1-051", lambda: accepted(skillTags=["高数", "线代", "英语", "跑步", "摄影"]))
    runner.run("S1-052", lambda: rejected(skillTags=["1", "2", "3", "4", "5", "6"]))
    runner.run("S1-053", lambda: accepted(remark="一" * 200))
    runner.run("S1-054", lambda: rejected(remark="一" * 201))

    # Supplemental evidence (not part of the 80-case catalogue).
    def utc_time():
        # The miniprogram sends new Date(...).toISOString(), i.e. trailing Z.
        accepted(time="2026-11-15T02:00:00.000Z")

    runner.run("API-NEEDS-UTC-TIME", utc_time)

    def bad_time():
        before = stack.count("buddy_demand")
        status, _, _ = submit(time="not-a-time")
        expect(status == 400, f"Invalid ISO time must be rejected, received {status}")
        expect(stack.count("buddy_demand") == before, "Bad time must not create a row")

    runner.run("API-NEEDS-BAD-TIME", bad_time)

    def moderation_block():
        before = stack.count("buddy_demand")
        status, _, _ = submit(remark="一起去图书馆 傻逼")
        expect(status == 422, f"HIGH hit must be blocked with 422, received {status}")
        expect(stack.count("buddy_demand") == before, "Blocked content must not be persisted")

    runner.run("API-NEEDS-MODERATION-422", moderation_block)

    def no_v1_list_route():
        # Listing/filtering is V1.0 #12; the old /api/buddy/list must not exist.
        status, _ = client.request("/api/buddy/list")
        expect(status == 404, f"V1.0 list route must stay absent, received {status}")

    runner.run("API-NEEDS-NO-V1-LIST", no_v1_list_route)
