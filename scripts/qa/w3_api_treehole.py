"""Ten HTTP treehole contracts, including actual MySQL and Redis observations."""

import hashlib
import json
import re
import uuid

from regression_http import expect


def register(runner, stack):
    client = runner.client
    route = "/api/treehole/posts"
    private_fields = {"userId", "anonymousId", "openid", "studentNo", "phone"}

    def public(body):
        expect(isinstance(body, dict), "Public post must be a JSON object")
        expect(not (private_fields & body.keys()), "Public post exposed private identity fields")
        expect(type(body.get("anonymous")) is bool, "Anonymous flag must be boolean")
        if body["anonymous"]:
            expect(re.fullmatch(r"anon_v1_[A-Za-z0-9_-]{43}", body.get("authorMask", "")),
                   "Anonymous author mask must be purpose-scoped HMAC")

    def create(content=None, **changes):
        text = content if content is not None else "W3 synthetic " + uuid.uuid4().hex
        data = {"content": text, "emotionTag": "CALM", **changes}
        before = stack.snapshot()
        status, body = client.request(route, data)
        expect(status == 201, f"Expected HTTP 201, received {status}")
        after = stack.snapshot()
        expect(after == {key: count + 1 for key, count in before.items()},
               "Published post must add exactly one MySQL and one Redis queue record")
        public(body)
        expect(body["content"] == text and body["emotionTag"] == data["emotionTag"],
               "Published content/tag differs from submitted values")
        identifier = str(int(body["id"]))
        persisted = stack.sql(
            "SELECT SHA2(content,256),emotion_tag,anonymous FROM treehole_post WHERE id="
            + identifier
        ).split("\t")
        expect(persisted == [hashlib.sha256(text.encode()).hexdigest(), data["emotionTag"],
                              str(int(body["anonymous"]))],
               "MySQL post fields must match submitted content, tag and anonymous flag")
        stored_alias = stack.sql("SELECT anonymous_id FROM treehole_post WHERE id=" + identifier)
        expect(re.fullmatch(r"anon_v1_[A-Za-z0-9_-]{43}", stored_alias),
               "Stored anonymous identity must be a purpose-scoped HMAC")
        if body["anonymous"]:
            expect(stored_alias == body["authorMask"], "Anonymous mask must match stored alias")
        expect(stack.redis("ZSCORE", "treehole:burn_queue", identifier) != "",
               "Published post must have a scheduled burn entry")
        client.observations.append({"mysql_rows_added": 1, "redis_queue_entries_added": 1})
        return body

    def default_anonymous():
        expect(create()["anonymous"] is True, "Omitted anonymous flag must default to true")

    def explicit_anonymous():
        first, second = create(anonymous=True), create(anonymous=True)
        expect(first["anonymous"] is True and second["anonymous"] is True,
               "Explicit anonymous flag must remain true")
        expect(first["authorMask"] == second["authorMask"],
               "Same user and purpose must produce a stable anonymous mask")
        client.observations.append({"purpose_scoped_mask_stable": True})

    def named():
        nickname = stack.sql("SELECT nickname FROM users WHERE id=1")
        body = create(anonymous=False)
        expect(body["anonymous"] is False, "Named post must remain named")
        expect(body["authorMask"] == (nickname or "用户"), "Named post must use public nickname")

    def rejected(data, expected):
        before = stack.snapshot()
        status, body = client.request(route, data)
        expect(status == expected, f"Expected HTTP {expected}, received {status}")
        expect(stack.snapshot() == before, "Rejected publication must not write MySQL or Redis")
        text = data.get("content")
        if text and len(text) > 3:
            expect(text not in json.dumps(body, ensure_ascii=False), "Error must not echo input")
        client.observations.append({"mysql_rows_added": 0, "redis_queue_entries_added": 0})

    runner.run("W3-TREEHOLE-01", default_anonymous)
    runner.run("W3-TREEHOLE-02", explicit_anonymous)
    runner.run("W3-TREEHOLE-03", named)
    runner.run("W3-TREEHOLE-04",
               lambda: rejected({"content": "你是傻逼", "emotionTag": "CALM"}, 422))
    runner.run("W3-TREEHOLE-05", lambda: create("好" * 500))
    runner.run("W3-TREEHOLE-06",
               lambda: rejected({"content": "好" * 501, "emotionTag": "CALM"}, 400))
    runner.run("W3-TREEHOLE-07", lambda: rejected({"emotionTag": "CALM"}, 400))
    runner.run("W3-TREEHOLE-08", lambda: rejected(
        {"content": "W3 synthetic invalid tag", "emotionTag": "UNKNOWN"}, 400))

    def filter_posts():
        created = create(emotionTag="ANXIOUS")
        status, body = client.request(route + "?emotionTag=ANXIOUS")
        expect(status == 200 and body["items"], "Tag query must return seeded content")
        expect(created["id"] in {post["id"] for post in body["items"]},
               "Latest filtered page must include the seeded post")
        for post in body["items"]:
            public(post)
            expect(post["emotionTag"] == "ANXIOUS", "Tag query leaked a different emotion")

    runner.run("W3-TREEHOLE-09", filter_posts)

    def pages():
        seeded = {create(emotionTag="IRRITABLE")["id"] for _ in range(12)}
        status, first = client.request(route + "?emotionTag=IRRITABLE")
        expect(status == 200 and len(first["items"]) == 10, "First page must contain ten rows")
        expect(first["nextCursor"] == "2", "First page must provide the second-page cursor")
        status, second = client.request(route + "?emotionTag=IRRITABLE&cursor=2")
        expect(status == 200, "Second page must return 200")
        first_ids, second_ids = ({post["id"] for post in page["items"]}
                                 for page in (first, second))
        expect(not first_ids & second_ids, "Adjacent pages must not repeat records")
        expect(seeded <= first_ids | second_ids, "Adjacent pages must include all twelve seeds")
        for post in first["items"] + second["items"]:
            public(post)
        client.observations.append({"pages_checked": 2, "unique_seeded_posts_returned": 12})

    runner.run("W3-TREEHOLE-10", pages)
