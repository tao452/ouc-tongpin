"""Treehole publishing, anonymous response, pagination, timeout and expiry regression."""

import hashlib
import json
import re
import time

from regression_http import expect


def register(runner, stack):
    client = runner.client
    route = "/api/treehole/posts"
    expired = {}

    def create(text="regression synthetic content", **changes):
        payload = {"content": text, "emotionTag": "CALM", **changes}
        before = stack.snapshot()
        status, body = client.request(route, payload)
        expect(status == 201, f"Expected HTTP 201, received {status}")
        expect(
            stack.snapshot() == {key: value + 1 for key, value in before.items()},
            "Publication must add exactly one database and queue record",
        )
        expect(body["content"] == text, "Publication changed content")
        expect(
            not ({"userId", "anonymousId", "openid", "studentNo", "phone"} & body.keys()),
            "Publication exposed internal identity fields",
        )
        expect(type(body["anonymous"]) is bool, "Anonymous flag must be boolean")
        if body["anonymous"]:
            expect(
                re.fullmatch(r"anon_v1_[A-Za-z0-9_-]{43}", body["authorMask"]),
                "Anonymous author mask is not purpose-scoped HMAC",
            )
        return body

    def anonymous(explicit):
        changes = {"anonymous": True} if explicit else {}
        body = create(**changes)
        expect(body["anonymous"] is True, "Default/explicit anonymous flag was lost")

    runner.run("S1-031", lambda: anonymous(False))
    runner.run("S1-032", lambda: anonymous(True))

    def named():
        stack.sql("UPDATE users SET nickname='Regression Nickname' WHERE id=1")
        body = create(anonymous=False)
        expect(body["authorMask"] == "Regression Nickname", "Named post must display nickname")

    runner.run("S1-033", named)

    def rejected(payload, expected):
        before = stack.snapshot()
        status, body = client.request(route, payload)
        expect(status == expected, f"Expected HTTP {expected}, received {status}")
        expect(stack.snapshot() == before, "Rejected publication changed database or Redis")
        text = payload.get("content")
        if text and len(text) > 3:
            expect(text not in json.dumps(body, ensure_ascii=False), "Error echoed user content")
        client.observations.append({"before": before, "after": stack.snapshot()})

    runner.run("S1-034", lambda: rejected({"content": "你是傻逼", "emotionTag": "CALM"}, 422))

    def timeout():
        try:
            stack.execute("pause", "algo")
            started = time.monotonic()
            rejected({"content": "regression timeout synthetic content", "emotionTag": "CALM"}, 503)
            expect(time.monotonic() - started >= 2.5, "Fault did not exercise the read timeout")
            client.observations.append({"fault": "algorithm container paused; read timeout"})
        finally:
            stack.execute("unpause", "algo")

    runner.run("S1-035", timeout)
    runner.run("S1-036", lambda: create("好" * 500))
    for number, payload in (
        (37, {"content": "好" * 501, "emotionTag": "CALM"}),
        (38, {"emotionTag": "CALM"}),
        (39, {"content": "regression missing tag"}),
        (40, {"content": "regression invalid tag", "emotionTag": "UNKNOWN"}),
    ):
        runner.run(f"S1-{number:03}", lambda p=payload: rejected(p, 400))

    def tag_filter():
        create(emotionTag="ANXIOUS")
        status, body = client.request(route + "?emotionTag=ANXIOUS")
        expect(status == 200 and body["items"], "Tag filter returned no seeded records")
        expect(
            all(row["emotionTag"] == "ANXIOUS" for row in body["items"]), "Tag filter leaked rows"
        )
        expect(
            all("userId" not in row for row in body["items"]), "List exposed internal identities"
        )

    runner.run("S1-041", tag_filter)

    def pages():
        expected_ids = {
            create(f"regression page {i}", emotionTag="IRRITABLE")["id"] for i in range(12)
        }
        status, first = client.request(route + "?emotionTag=IRRITABLE")
        expect(status == 200 and len(first["items"]) == 10, "First page size differs")
        expect(first["nextCursor"] == "2", "First page did not return the numeric-page cursor")
        status, second = client.request(route + "?emotionTag=IRRITABLE&cursor=2")
        expect(status == 200 and len(second["items"]) == 2, "Second page size differs")
        first_ids, second_ids = ({row["id"] for row in page["items"]} for page in (first, second))
        expect(not first_ids & second_ids, "Pagination repeated records")
        expect(first_ids | second_ids == expected_ids, "Pagination omitted seeded records")
        client.observations.append({"pages": 2, "distinct_posts": 12})

    runner.run("S1-042", pages)

    def last_page():
        for cursor, count in ((2, 2), (3, 0)):
            status, body = client.request(route + f"?emotionTag=IRRITABLE&cursor={cursor}")
            expect(status == 200 and len(body["items"]) == count, "Last/empty page differs")
            expect(body["nextCursor"] is None, "Last page must have null nextCursor")

    runner.run("S1-043", last_page)

    def hidden_expiry():
        post = create("regression expired content", emotionTag="LONELY")
        identifier = int(post["id"])
        expired.update(id=identifier, content=post["content"])
        stack.sql(f"UPDATE treehole_post SET expires_at='2000-01-01' WHERE id={identifier}")
        status, body = client.request(route + "?emotionTag=LONELY")
        expect(
            status == 200 and all(row["id"] != identifier for row in body["items"]),
            "Expired content remained visible while waiting for burn scheduler",
        )

    runner.run("S1-044", hidden_expiry)

    def burned_storage():
        expect("id" in expired, "Expiry fixture was not created")
        identifier = expired["id"]
        stack.redis(
            "ZADD", "treehole:burn_queue", str(int(time.time() * 1000) - 1000), str(identifier)
        )
        for _ in range(50):
            if (stack.sql(f"SELECT status FROM treehole_post WHERE id={identifier}") == "1"
                    and stack.redis("ZSCORE", "treehole:burn_queue", str(identifier)) == ""):
                break
            time.sleep(0.5)
        expect(
            stack.sql(f"SELECT status FROM treehole_post WHERE id={identifier}") == "1",
            "Burn scheduler did not process the expired record",
        )
        content = stack.sql(f"SELECT content FROM treehole_post WHERE id={identifier}")
        expect(expired["content"] not in content, "Burned record retained original content")
        digest = hashlib.md5(expired["content"].encode(), usedforsecurity=False).hexdigest()
        archived = stack.sql(
            f"SELECT content_hash FROM treehole_archive WHERE post_id={identifier}"
        )
        expect(archived == digest, "Archive differs from original content hash")
        expect(
            stack.redis("ZSCORE", "treehole:burn_queue", str(identifier)) == "",
            "Burned queue entry was not removed",
        )
        client.observations.append(
            {
                "burned_status": 1,
                "original_content_removed": True,
                "archive_hash_matches": True,
                "queue_entry_removed": True,
            }
        )

    runner.run("S1-046", burned_storage)
