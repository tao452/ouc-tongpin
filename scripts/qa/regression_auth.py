"""Input boundaries and explicitly scoped mock-login regression, not WeChat acceptance."""

import json
import uuid

from regression_http import expect


def register(runner, stack):
    client = runner.client
    route = "/api/auth/login"

    def invalid():
        before = (stack.count("users"), stack.count("auth"))
        for payload in ({}, {"code": ""}, {"code": " "}, {"code": None}):
            status, _ = client.request(route, payload)
            expect(status == 400, "Missing or blank code must return 400")
        expect(
            (stack.count("users"), stack.count("auth")) == before,
            "Rejected login created account or authentication rows",
        )
        client.observations.append({"invalid_requests": 4, "database_rows_added": 0})

    runner.run("S1-004", invalid)

    def mock_flow():
        before = (stack.count("users"), stack.count("auth"))
        payload = {"code": "regression-synthetic-" + uuid.uuid4().hex}
        status, body = client.request(route, payload)
        expect(status == 200, "Synthetic mock login failed")
        expect(
            set(body) == {"token", "userId", "isNewUser", "needStudentVerify"},
            "Login response differs from contract",
        )
        expect(
            isinstance(body["token"], str) and len(body["token"].split(".")) == 3,
            "Login did not return a JWT-shaped token",
        )
        expect(
            body["isNewUser"] is True and body["needStudentVerify"] is True,
            "New unverified mock user has incorrect flags",
        )
        after = (stack.count("users"), stack.count("auth"))
        expect(after == tuple(count + 1 for count in before), "Mock login failed to persist")
        status, repeated = client.request(route, payload)
        expect(status == 200 and repeated["userId"] == body["userId"], "Mock identity is unstable")
        expect(repeated["isNewUser"] is False, "Existing mock user reported as new")
        expect((stack.count("users"), stack.count("auth")) == after, "Mock identity duplicated")
        client.observations.append(
            {
                "mock_identity_stable": True,
                "account_rows_added": 1,
                "auth_rows_added": 1,
                "token_shape_valid": True,
            }
        )

    runner.run(
        "API-AUTH-MOCK-CONTRACT",
        mock_flow,
        "Synthetic code2session mock and actual MySQL, not real WeChat code/JWT authorization",
    )

    def malformed():
        before = (stack.count("users"), stack.count("auth"))
        status, body = client.request(route, raw=b'{"code":"PRIVATE-MALFORMED')
        expect(status == 400, "Malformed JSON must return 400")
        expect("PRIVATE-MALFORMED" not in json.dumps(body), "Error echoed request content")
        expect(
            (stack.count("users"), stack.count("auth")) == before, "Malformed login mutated data"
        )

    runner.run("API-AUTH-MALFORMED", malformed)
