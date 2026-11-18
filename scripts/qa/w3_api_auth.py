"""Six real HTTP checks of the current synthetic code2session login contract."""

import json
import uuid

from regression_http import expect


def register(runner, stack):
    client = runner.client
    route = "/api/auth/login"

    def counts():
        return stack.count("users"), stack.count("auth")

    def login(code):
        status, body = client.request(route, {"code": code})
        expect(status == 200, "Synthetic mock login must return 200")
        expect(isinstance(body, dict), "Login must return a JSON object")
        expect(set(body) == {"token", "userId", "isNewUser", "needStudentVerify"},
               "Login response must match its public contract")
        expect(isinstance(body["token"], str) and len(body["token"].split(".")) == 3,
               "Login must return a JWT-shaped token")
        expect(str(body["userId"]).isdigit(), "Login must return a numeric user identifier")
        expect(body["needStudentVerify"] is True, "Synthetic unverified user needs verification")
        return body

    def new_user():
        before = counts()
        body = login("w3-synthetic-" + uuid.uuid4().hex)
        expect(body["isNewUser"] is True, "First mock login must create a user")
        expect(counts() == tuple(n + 1 for n in before),
               "First login must persist exactly one user and one private auth row")
        client.observations.append({"user_rows_added": 1, "private_auth_rows_added": 1})

    def repeat_user():
        code = "w3-synthetic-" + uuid.uuid4().hex
        first = login(code)
        before = counts()
        repeated = login(code)
        expect(repeated["userId"] == first["userId"], "Repeated mock identity must be stable")
        expect(repeated["isNewUser"] is False, "Repeated mock login must report existing user")
        expect(counts() == before, "Repeated login must not duplicate users or private auth rows")
        client.observations.append({"identity_stable": True, "database_rows_added_on_repeat": 0})

    def rejected(payload=None, raw=None):
        before = counts()
        status, body = client.request(route, payload=payload, raw=raw)
        expect(status == 400, "Invalid login must return 400")
        expect(counts() == before, "Rejected login must not create user or auth rows")
        expect("W3-PRIVATE-MALFORMED" not in json.dumps(body), "Error must not echo input")
        client.observations.append({"database_rows_added": 0})

    scope = "Real HTTP and MySQL, synthetic code2session mock; no real WeChat authorization"
    runner.run("W3-AUTH-01", new_user, scope)
    runner.run("W3-AUTH-02", repeat_user, scope)
    runner.run("W3-AUTH-03", lambda: rejected({}), scope)
    runner.run("W3-AUTH-04", lambda: rejected({"code": " \t "}), scope)
    runner.run("W3-AUTH-05", lambda: rejected({"code": None}), scope)
    runner.run("W3-AUTH-06", lambda: rejected(raw=b'{"code":"W3-PRIVATE-MALFORMED'), scope)
