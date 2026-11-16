"""Real JWT/ownership checks against the disposable CI API; no raw identity evidence."""

import base64
import concurrent.futures
import hashlib
import hmac
import json
import secrets
from datetime import date, timedelta

from regression_http import Client, expect


def signed_claims(actor, key, **changes):
    parts = actor.token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    claims.update(changes)
    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
    payload = encode(json.dumps(claims, separators=(",", ":")).encode())
    content = parts[0] + "." + payload
    signature = encode(hmac.new(key.encode(), content.encode(), hashlib.sha256).digest())
    return content + "." + signature


def register(runner, stack, key):
    alice = runner.client
    bob_code = "us25-b-" + secrets.token_hex(12)
    bob = Client(alice.base).authenticate(bob_code)
    guest = Client(alice.base)
    day = (date(2040, 1, 1) + timedelta(days=secrets.randbelow(900_000))).isoformat()
    route = "/api/emotions/checkins"
    records = {}
    material = []

    def ask(actor, path, payload=None, **kwargs):
        if actor is not alice:
            actor.observations.clear()
        status, body = actor.request(path, payload, **kwargs)
        if actor is not alice:
            alice.observations.extend(actor.observations)
        material.append(json.dumps(body, ensure_ascii=False))
        return status, body

    def denied(actor, path=route, payload=None, **kwargs):
        tables = ("checkin", "treehole_post", "buddy_demand")
        before = {table: stack.count(table) for table in tables}
        status, _ = ask(actor, path, payload, **kwargs)
        expect(status == 401, "Unauthorized caller was not rejected")
        expect(before == {table: stack.count(table) for table in before},
               "Unauthorized request changed business rows")

    runner.run("US25-01", lambda: denied(guest))
    runner.run("US25-02", lambda: [denied(guest, path, {})
                                   for path in ("/api/treehole/posts", "/api/match/needs")])
    runner.run("US25-03", lambda: [denied(guest, headers={"Authorization": header})
                                   for header in ("Basic invalid", "Bearer invalid", "Bearer ")])

    def signatures():
        # Positive signed control proves the fixture key really matches this API.
        control = signed_claims(alice, key)
        expect(ask(guest, route, headers={"Authorization": "Bearer " + control})[0] == 200,
               "Signed-token positive control failed")
        for token in (signed_claims(alice, key, exp=1),
                      signed_claims(alice, key, aud="another-app"),
                      signed_claims(alice, "wrong-fixture-key")):
            denied(guest, headers={"Authorization": "Bearer " + token})
    runner.run("US25-04", signatures)
    runner.run("US25-05", lambda: denied(guest, route + "?token=" + alice.token))

    def lookup_privacy():
        rows = stack.sql("SELECT openid FROM auth "
                         f"WHERE user_id IN ({alice.user_id},{bob.user_id})").splitlines()
        valid = len(rows) == 2 and all(row.startswith("anon_v1_") and len(row) == 51
                                      for row in rows)
        expect(valid,
               "Provider identity must be stored only as a scoped HMAC lookup")
        alice.observations.append({"hashed_identity_rows": 2})
    runner.run("US25-06", lookup_privacy)

    def separate_checkins():
        for label, actor in (("a", alice), ("b", bob)):
            payload = {"emotion": "CALM", "intensity": 3, "checkinDate": day,
                       "note": "private-" + label, "userId": bob.user_id}
            status, body = ask(actor, route, payload)
            expect(status == 200 and "userId" not in body, "Private check-in contract failed")
            records[label] = int(body["id"])
            owner = stack.sql(f"SELECT user_id FROM checkin WHERE id={records[label]}")
            expect(owner == str(actor.user_id), "An untrusted owner changed persistence identity")
        expect(records["a"] != records["b"], "Different users shared one private check-in")
    runner.run("US25-07", separate_checkins)

    def isolated_query():
        for label, actor, other in (("a", alice, bob), ("b", bob, alice)):
            status, body = ask(actor, route + f"?from={day}&to={day}&userId={other.user_id}")
            expect(status == 200 and len(body["items"]) == 1, "Private query was not isolated")
            expect(body["items"][0]["note"] == "private-" + label,
                   "Another account's private note was returned")
    runner.run("US25-08", isolated_query)

    def spoofed_update():
        status, body = ask(bob, route, {"emotion": "HAPPY", "intensity": 5,
                                     "checkinDate": day, "userId": alice.user_id,
                                     "id": records["a"], "note": "overwrite-attempt"})
        expect(status == 200 and int(body["id"]) == records["b"], "Cross-owner write was accepted")
        expect(stack.sql(f"SELECT note FROM checkin WHERE id={records['a']}") == "private-a",
               "Victim's existing check-in was overwritten")
    runner.run("US25-09", spoofed_update)
    runner.run("US25-10", lambda: (isolated_query(), denied(guest)))

    def anonymous_posts():
        masks = []
        for actor in (alice, bob):
            status, body = ask(actor, "/api/treehole/posts", {"content": "US25 public fixture",
                              "emotionTag": "CALM", "anonymous": True, "userId": bob.user_id})
            expect(status == 201 and not {"userId", "openid", "phone", "studentNo"} & body.keys(),
                   "Public post exposed private identity fields")
            owner = stack.sql("SELECT user_id FROM treehole_identity WHERE post_id="
                              + str(int(body["id"])))
            expect(owner == str(actor.user_id), "Anonymous mapping used an untrusted owner")
            masks.append(body["authorMask"])
        expect(masks[0] != masks[1], "Different accounts share one anonymous identity")
    runner.run("US25-11", anonymous_posts)

    def privileged_routes():
        elevated = signed_claims(alice, key, roles=["ADMIN"])
        for path in ("/api/admin/identities", "/api/privacy/identities", "/api/auth/identities"):
            expect(ask(guest, path, headers={"Authorization": "Bearer " + elevated})[0] == 403,
                   "A normal caller gained privileged access from token role claims")
    runner.run("US25-12", privileged_routes)

    def missing_object_writes():
        for method in ("DELETE", "PUT"):
            expect(ask(bob, route + "/" + str(records["a"]), method=method)[0] in {404, 405},
                   "Unimplemented object mutation unexpectedly accepted a request")
        isolated_query()
    runner.run("US25-13", missing_object_writes)

    def parallel_queries():
        def query(index):
            actor, expected = (alice, "private-a") if index % 2 else (bob, "private-b")
            other = Client(actor.base, token=actor.token)
            status, body = other.request(route + f"?from={day}&to={day}")
            return status == 200 and body["items"][0]["note"] == expected
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            expect(all(pool.map(query, range(24))), "Concurrent queries crossed account boundaries")
        alice.observations.append({"isolated_concurrent_queries": 24})
    runner.run("US25-14", parallel_queries)

    def concurrent_logins():
        before = (stack.count("users"), stack.count("auth"))
        code = "us25-concurrent-" + secrets.token_hex(12)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            users = list(pool.map(lambda _: Client(alice.base).authenticate(code).user_id,
                                  range(4)))
        expect(len(set(users)) == 1, "Concurrent login created multiple identities")
        expect((stack.count("users"), stack.count("auth")) == tuple(n + 1 for n in before),
               "Concurrent identity registration left orphan or duplicate rows")
        alice.observations.append({"concurrent_logins": 4, "distinct_identities": 1})
    runner.run("US25-15", concurrent_logins)

    def inactive_account():
        stack.sql(f"UPDATE users SET deleted=1 WHERE id={bob.user_id}")
        denied(bob)
        expect(ask(guest, "/api/auth/login", {"code": bob_code})[0] == 401,
               "Disabled identity obtained a new token")
    runner.run("US25-16", inactive_account)
    return (alice, bob), material, [bob_code]
