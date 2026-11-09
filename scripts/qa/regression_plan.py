"""Explicit priority and external prerequisites for all 80 catalogue cases."""

P1 = {13, 14, 15, 16, 17, 18, 28, 29, 30, 41, 42, 43}
EXTERNAL = {
    **{n: "java-privacy" for n in range(69, 76)},
    **{n: "compose-stack" for n in range(77, 80)},
}


def priority(identifier):
    return "P1" if int(identifier.rsplit("-", 1)[1]) in P1 else "P0"


def register_blocked(runner):
    for number in (1, 2, 3, 5, 6):
        runner.blocked(
            f"S1-{number:03}",
            "AuthService still uses mock code2session; real WeChat code/account required",
            [{"implementation": "mock code2session", "formal_wechat_acceptance": False}],
        )

    def missing_route(path):
        runner.client.observations.clear()
        status, _ = runner.client.request(path, {})
        observations = list(runner.client.observations)
        if status != 404:
            raise AssertionError("Declared missing endpoint no longer returns 404; update the plan")
        return observations

    auth = missing_route("/api/auth/student-verify")
    for number in range(7, 13):
        runner.blocked(
            f"S1-{number:03}",
            "Student verification/screenshot authorization endpoint is not implemented",
            auth,
        )
    runner.blocked(
        "S1-030", "Final consecutive/missed-day product rule awaits M1; technical API covered"
    )
    runner.client.observations.clear()
    status, _ = runner.client.request("/api/treehole/posts/999999999")
    if status != 404:
        raise AssertionError("Treehole detail endpoint changed; update its acceptance plan")
    runner.blocked(
        "S1-045",
        "Treehole detail endpoint is not implemented; 404 is not expiry acceptance",
        list(runner.client.observations),
    )
    needs = missing_route("/api/match/needs")
    for number in range(47, 55):
        runner.blocked(
            f"S1-{number:03}", "Match needs publishing endpoint is not implemented", needs
        )
    runner.blocked(
        "S1-076", "JWT caller identity and identity-mapping authorization await integration"
    )
    runner.blocked(
        "S1-080",
        "Branch protection API returned 404 to current account; admin proof pending. "
        "Historical failed-quality experiment exists in PR #53",
    )
