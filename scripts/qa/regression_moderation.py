"""Moderation contract regression; keep unapproved product acceptance explicitly blocked."""

from regression_http import expect


def register(runner, stack):
    client = runner.client
    route = "/api/moderation/check"

    def check(text, passed, level=None, expected=200):
        status, body = client.request(route, {"text": text})
        expect(status == expected, f"Expected HTTP {expected}, received {status}")
        if status == 200:
            expect(set(body) == {"passed", "normalized", "hits"}, "Moderation response keys differ")
            expect(body["passed"] is passed, "Moderation decision differs")
            if level:
                expect(any(hit["level"] == level for hit in body["hits"]), "Expected level missing")
            else:
                expect(body["hits"] == [], "Benign text unexpectedly matched")
        else:
            expect(body == {"detail": "Invalid request"}, "Invalid input was echoed")

    runner.run("S1-055", lambda: check("一起去图书馆", True))
    runner.run("S1-056", lambda: check("傻逼", False, "HIGH"))
    for number, text, level in ((57, "废物", "MEDIUM"), (58, "垃圾", "LOW")):
        runner.run(f"S1-{number:03}", lambda t=text, level=level: check(t, True, level))
        if runner.results[-1]["status"] == "PASS":
            runner.results[-1].update(
                status="BLOCKED",
                technical_assertions="PASS",
                reason="Baseline observed; formal dictionary/product acceptance pending M1",
            )

    def traditional():
        left = client.request(route, {"text": "操你媽"})
        right = client.request(route, {"text": "操你妈"})
        expect(
            left == right and left[0] == 200 and left[1]["passed"] is False,
            "Traditional/simplified decisions differ",
        )

    runner.run("S1-059", traditional)
    runner.run("S1-060", lambda: check("ＳＨＡＢＩ", False, "HIGH"))
    runner.run("S1-061", lambda: check("煞笔", False, "HIGH"))

    def pinyin():
        check("shabi", False, "HIGH")
        check("shabilist", True)

    runner.run("S1-062", pinyin)
    runner.run("S1-063", lambda: check("傻*\u200b逼", False, "HIGH"))
    runner.run("S1-064", lambda: check(" ", None, expected=422))
    runner.run("S1-065", lambda: check("好" * 2000, True))
    runner.run("S1-066", lambda: check("好" * 2001, None, expected=422))

    def malformed():
        status, body = client.request(route, raw=b"{")
        expect(
            status == 422 and body == {"detail": "Invalid request"}, "Invalid JSON was not rejected"
        )

    runner.run("S1-067", malformed)

    def limit():
        status, _ = client.request(route, raw=b"x" * 16385)
        direct = stack.direct_body_limit()
        expect(status == direct == 413, "Direct/gateway body limits differ")
        client.observations.append({"direct_http_status": direct, "gateway_http_status": status})

    runner.run("S1-068", limit)
