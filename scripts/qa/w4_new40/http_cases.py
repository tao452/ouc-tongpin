"""Real network and owned-storage cases; assertions follow the reviewed design."""

import base64
import hashlib
import hmac
import http.client
import json
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DAY = "2034-01-15"


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def signed(s, actor, changes=None, length=None):
    claims = {
        "sub": str(actor["id"]),
        "iss": "ouc-tongpin",
        "aud": "ouc-miniprogram",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    for key, value in (changes or {}).items():
        if value is None:
            claims.pop(key, None)
        else:
            claims[key] = value

    def build(padding=None):
        value = dict(claims)
        if padding is not None:
            value["padding"] = "x" * padding
        prefix = (
            b64(b'{"alg":"HS256","typ":"JWT"}')
            + "."
            + b64(json.dumps(value, separators=(",", ":")).encode())
        )
        return (
            prefix
            + "."
            + b64(
                hmac.new(
                    s.env["JWT_SECRET"].encode(), prefix.encode(), hashlib.sha256
                ).digest()
            )
        )

    if length is None:
        return build()
    for padding in range(length):
        value = build(padding)
        if len(value) == length:
            return value
    raise RuntimeError("Unable to construct exact signed JWT length")


def batch(s, functions, workers=16):
    barrier = threading.Barrier(min(workers, len(functions)))

    def job(index, fn):
        if index < workers:
            barrier.wait(10)
        return fn()

    return s.parallel(
        [lambda i=i, fn=fn: job(i, fn) for i, fn in enumerate(functions)], workers
    )


def stable(body):
    return {
        k: body.get(k) for k in ["id", "emotion", "intensity", "note", "checkinDate"]
    }


def register(s):
    def c81():
        a, b = s.actor(), s.actor()
        s.checkin(a, note="A-only")
        s.checkin(b, note="B-only")
        before = (s.snapshot(a), s.snapshot(b))
        for port in [s.base, s.direct]:
            for actor in [a, b]:
                assert (
                    s.http("/api/emotions/checkins", token=actor["token"], port=port)[0]
                    == 200
                )
            for left, right in [(a, b), (b, a)]:
                status, body, _ = s.http(
                    "/api/emotions/checkins",
                    port=port,
                    headers=[
                        ("Authorization", "Bearer " + left["token"]),
                        ("Authorization", "Bearer " + right["token"]),
                    ],
                )
                assert status in ([401] if port == s.direct else [400, 401])
                assert all(x not in json.dumps(body) for x in ["A-only", "B-only"])
        assert before == (s.snapshot(a), s.snapshot(b))

    s.run(81, c81)

    def c82():
        a = s.actor()
        before = s.snapshot(a)
        for length in [4096, 4097]:
            token = signed(s, a, length=length)
            assert len(token) == length
            for port in [s.base, s.direct]:
                status, _, _ = s.http("/api/emotions/checkins", token=token, port=port)
                s.record(
                    {
                        "kind": "token_fixture",
                        "signed": True,
                        "length": len(token),
                        "authorization_length": len(token) + 7,
                    }
                )
                assert status == (200 if length == 4096 else 401)
        assert before == s.snapshot(a)

    s.run(82, c82)

    def c83():
        a = s.actor()
        before = s.snapshot(a)
        for iat, expected in [
            (int(time.time()), 200),
            (None, 401),
            (int(time.time()) + 120, 401),
        ]:
            assert (
                s.http("/api/emotions/checkins", token=signed(s, a, {"iat": iat}))[0]
                == expected
            )
        assert before == s.snapshot(a)

    s.run(83, c83)

    def c84():
        a = s.actor()
        before = s.snapshot(a)
        assert s.http("/api/emotions/checkins", token=a["token"])[0] == 200
        for subject in [
            "0",
            "-1",
            "01",
            "1.0",
            "1e3",
            "9223372036854775808",
            " ",
            None,
        ]:
            assert (
                s.http("/api/emotions/checkins", token=signed(s, a, {"sub": subject}))[
                    0
                ]
                == 401
            )
        assert before == s.snapshot(a)

    s.run(84, c84)

    def c86():
        a, b = s.actor(), s.actor()
        s.checkin(b, note="B-private")
        assert s.http("/api/emotions/checkins", token=a["token"])[0] == 200
        s.sql(f"DELETE FROM users WHERE id={a['id']}")
        before = s.sql(f"SELECT COUNT(*) FROM users WHERE id={a['id']}")
        for _ in range(2):
            status, body, _ = s.http("/api/emotions/checkins", token=a["token"])
            assert status == 401 and "B-private" not in json.dumps(body)
        assert before == s.sql(f"SELECT COUNT(*) FROM users WHERE id={a['id']}") == "0"

    s.run(86, c86)

    def c88():
        a, b = s.actor(), s.actor()
        s.checkin(a, note="A-only")
        s.checkin(b, note="B-only")
        before = (s.snapshot(a), s.snapshot(b))
        cycle = [
            (a["token"], 200, "A-only"),
            (b["token"], 200, "B-only"),
            (None, 401, None),
            ("invalid", 401, None),
        ]
        jobs = [
            lambda token=t, expected=e, note=n: (
                s.http(f"/api/emotions/checkins?from={DAY}&to={DAY}", token=token),
                expected,
                note,
            )
            for t, e, n in cycle * 16
        ]
        for (status, body, _), expected, note in batch(s, jobs, 8):
            assert status == expected
            if note:
                assert len(body["items"]) == 1 and body["items"][0]["note"] == note
        assert s.http("/api/emotions/checkins")[0] == 401
        assert before == (s.snapshot(a), s.snapshot(b))

    s.run(88, c88)

    def c89():
        a = s.actor()
        before = s.snapshot(a)
        _, _, headers = s.http("/api/emotions/checkins", token=a["token"])
        assert "JSESSIONID" not in str(headers)
        for cookie in [
            "JSESSIONID=w4-synthetic",
            "token=" + a["token"],
            "Authorization=Bearer%20" + a["token"],
        ]:
            status, body, _ = s.http(
                "/api/emotions/checkins", headers=[("Cookie", cookie)]
            )
            assert status == 401 and a["token"] not in json.dumps(body)
        assert s.http("/api/emotions/checkins", token=a["token"])[0] == 200
        assert before == s.snapshot(a)

    s.run(89, c89)

    def c90():
        a, b = s.actor(), s.actor()
        body = s.need()
        body.update(userId=b["id"], ownerId=b["id"])
        before = s.buddy_count(a), s.buddy_count(b)
        status, res, _ = s.http(
            f"/api/match/needs?userId={b['id']}",
            body,
            a["token"],
            headers=[("X-User-Id", str(b["id"]))],
        )
        assert status == 201 and set(res) == {"id", "scene", "status"}
        assert s.sql(
            "SELECT user_id FROM buddy_demand WHERE id=" + str(int(res["id"]))
        ) == str(a["id"])
        assert (s.buddy_count(a), s.buddy_count(b)) == (before[0] + 1, before[1])

    s.run(90, c90)

    def c91():
        a = s.actor()
        _, first, _ = s.checkin(a)
        before = s.snapshot(a)
        results = batch(
            s,
            [lambda: s.checkin(a, emotion="CALM", intensity=5, note="retry-change")]
            * 16,
            8,
        )
        assert all(
            code == 200 and stable(body) == stable(first) for code, body, _ in results
        )
        assert before == s.snapshot(a)

    s.run(91, c91)

    def c92():
        a = s.actor()
        assert s.snapshot(a) == ""
        candidates = [
            {"emotion": "HAPPY", "intensity": 1, "note": "candidate-A"},
            {"emotion": "CALM", "intensity": 5, "note": "candidate-B"},
        ]
        results = batch(s, [lambda p=p: s.checkin(a, **p) for p in candidates * 16])
        assert all(code == 200 for code, _, _ in results)
        first = stable(results[0][1])
        assert all(stable(body) == first for _, body, _ in results)
        assert {k: first[k] for k in candidates[0]} in candidates
        assert len(s.snapshot(a).splitlines()) == 1

    s.run(92, c92)

    def c93():
        a = s.actor()
        jobs = [
            lambda d=d, note=n: (s.checkin(a, d, note=note), d, note)
            for d, n in [(DAY, "day-0"), ("2034-01-16", "day-1")] * 16
        ]
        groups = {}
        for (status, body, _), day, note in batch(s, jobs):
            assert status == 200 and body["checkinDate"] == day and body["note"] == note
            groups.setdefault(day, set()).add(body["id"])
        assert all(len(ids) == 1 for ids in groups.values())
        assert len(set.union(*groups.values())) == 2
        assert len(s.snapshot(a).splitlines()) == 2

    s.run(93, c93)

    def c94():
        a, b = s.actor(), s.actor()
        jobs = [
            lambda actor=x, other=y, note=n: (
                s.checkin(actor, note=note, userId=other["id"]),
                actor,
                note,
            )
            for x, y, n in [(a, b, "owner-A"), (b, a, "owner-B")] * 16
        ]
        ids = {}
        for (status, body, _), actor, note in batch(s, jobs):
            assert status == 200 and body["note"] == note
            ids.setdefault(actor["id"], set()).add(body["id"])
        assert (
            all(len(v) == 1 for v in ids.values())
            and len(set.union(*ids.values())) == 2
        )
        assert all(len(s.snapshot(actor).splitlines()) == 1 for actor in [a, b])

    s.run(94, c94)

    def c95():
        a = s.actor()
        jobs = []
        for change, expected, count in [
            ({}, 200, 16),
            ({"intensity": 0}, 400, 8),
            ({"emotion": "UNKNOWN"}, 400, 8),
        ]:
            for _ in range(count):
                jobs.append(
                    lambda p=change, e=expected: (
                        s.checkin(
                            a,
                            **{"emotion": "CALM", "intensity": 3, "note": "valid", **p},
                        ),
                        e,
                    )
                )
        for (status, _, _), expected in batch(s, jobs):
            assert status == expected
        result = s.snapshot(a)
        assert len(result.splitlines()) == 1 and "valid" in result

    s.run(95, c95)

    def c96():
        a = s.actor()
        captured = {}

        class Proxy(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                status, response, _ = s.http(self.path, body, a["token"])
                captured.update(status=status, body=response)
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        body = {
            "emotion": "HAPPY",
            "intensity": 3,
            "note": "lost-response",
            "checkinDate": DAY,
        }
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=25
        )
        try:
            connection.request(
                "POST",
                "/api/emotions/checkins",
                json.dumps(body),
                {"Content-Type": "application/json"},
            )
            try:
                connection.getresponse()
                raise AssertionError("Injected response loss did not occur")
            except http.client.RemoteDisconnected:
                s.record(
                    {
                        "kind": "fault_proxy",
                        "client_observation": "RemoteDisconnected",
                        "upstream_status": captured["status"],
                    }
                )
            assert captured["status"] == 200 and len(s.snapshot(a).splitlines()) == 1
            status, retried, _ = s.checkin(a, note="lost-response")
            assert status == 200 and stable(retried) == stable(captured["body"])
            assert len(s.snapshot(a).splitlines()) == 1
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(5)

    s.run(96, c96)

    def c97():
        code = "w4-cold-" + s.run_id
        before = [
            int(s.sql(f"SELECT COUNT(*) FROM {t}"))
            for t in ["users", "auth", "checkin"]
        ]

        def worker():
            actor = s.actor(code)
            return actor["id"], s.checkin(actor, note="cold-login")

        values = batch(s, [worker] * 16)
        assert len({uid for uid, _ in values}) == 1
        assert all(value[0] == 200 for _, value in values)
        assert len({value[1]["id"] for _, value in values}) == 1
        after = [
            int(s.sql(f"SELECT COUNT(*) FROM {t}"))
            for t in ["users", "auth", "checkin"]
        ]
        assert after == [n + 1 for n in before]

    s.run(97, c97)

    def c99():
        a = s.actor()
        before = datetime.now(timezone(timedelta(hours=8)))
        status, body, _ = s.post(a)
        after = datetime.now(timezone(timedelta(hours=8)))
        assert status == 201
        created = datetime.fromisoformat(body["createdAt"]).replace(
            tzinfo=before.tzinfo
        )
        expires = datetime.fromisoformat(body["expiresAt"]).replace(
            tzinfo=before.tzinfo
        )
        assert (
            expires - created
        ).total_seconds() == 86400 and before <= created <= after
        expected = int(expires.timestamp()) * 1000 + expires.microsecond // 1000
        assert (
            int(float(s.redis("ZSCORE", "treehole:burn_queue", body["id"]))) == expected
        )
        sql_value = s.sql(
            "SELECT DATE_FORMAT(expires_at,'%Y-%m-%dT%H:%i:%s') "
            "FROM treehole_post WHERE id=" + str(int(body["id"]))
        )
        persisted = datetime.fromisoformat(sql_value).replace(tzinfo=before.tzinfo)
        assert abs((persisted - expires).total_seconds()) < 1

    s.run(99, c99)

    for number in range(107, 113):

        def boundary(number=number):
            a = s.actor()
            variants = []
            if number == 107:
                variants = [
                    ({"scene": "习" * n}, 201 if n == 64 else 400) for n in [64, 65]
                ]
            if number == 108:
                variants = [
                    (
                        {"location": {**s.need()["location"], "address": "馆" * n}},
                        201 if n == 255 else 400,
                    )
                    for n in [255, 256]
                ]
            if number == 109:
                variants = [
                    ({"location": loc}, 400)
                    for loc in [
                        {},
                        *[
                            {"address": v, "lat": 36.16, "lng": 120.4}
                            for v in [None, "", "   "]
                        ],
                    ]
                ]
            if number == 110:
                variants = [
                    ({"time": value}, 201)
                    for value in ["2033-12-31T16:30:00Z", "2034-01-01T00:30:00+08:00"]
                ]
            if number == 111:
                variants = [
                    ({"time": value}, 400)
                    for value in [
                        "2033-02-29T10:00:00+08:00",
                        "2034-01-15T10:00:00+25:00",
                    ]
                ]
            if number == 112:
                variants = [
                    ({"omit": True}, 201),
                    ({"skillTags": None, "remark": None}, 201),
                    ({"skillTags": [], "remark": ""}, 201),
                ]
            ids = []
            for patch, expected in variants:
                body = s.need()
                if patch.pop("omit", False):
                    body.pop("skillTags")
                    body.pop("remark")
                body.update(patch)
                before = s.buddy_count(a)
                status, response, _ = s.buddy(a, body)
                assert status == expected, (number, status, expected)
                assert s.buddy_count(a) - before == (1 if expected == 201 else 0)
                if expected == 201:
                    assert set(response) == {"id", "scene", "status"}
                    pid = int(response["id"])
                    ids.append(pid)
                    row = s.sql(
                        "SELECT scene,location_address,event_time,skill_tags,remark "
                        f"FROM buddy_demand WHERE id={pid}"
                    ).split("\t")
                    assert (
                        row[0] == body["scene"]
                        and row[1] == body["location"]["address"]
                    )
                    if number == 110:
                        assert row[2] == "2034-01-01 00:30:00"
                    if number == 112:
                        assert row[3] == "NULL"
                        assert row[4] == ("NULL" if body.get("remark") is None else "")
            assert len(ids) == len(set(ids))

        s.run(number, boundary)
