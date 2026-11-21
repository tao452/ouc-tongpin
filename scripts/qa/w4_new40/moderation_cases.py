import json
import os
import subprocess
import time
import urllib.request

from common import ROOT, digest


def algorithm(s, text, port=None):
    status, body, _ = s.http("/api/moderation/check", {"text": text}, port=port)
    assert status == 200
    return body


def instance(s, records, action):
    here = ROOT / "qa-private/w4-closeout"
    target = here / "custom-dictionary.json"
    target.write_bytes((json.dumps(records, ensure_ascii=False) + "\n").encode())
    mount = target.as_posix()
    if os.name == "nt":
        mount = "/mnt/" + mount[0].lower() + mount[2:]
    command = s.docker
    name = s.project + "-dictionary-" + s.run_id

    def run(*args):
        return subprocess.run(
            [*command, *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    try:
        run(
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "w4.owner=" + s.project,
            "-p",
            "127.0.0.1:18090:8000",
            "-v",
            mount + ":/app/custom.json:ro",
            "-e",
            "MODERATION_DICTIONARY_PATH=/app/custom.json",
            s.command("images", "-q", "algo").splitlines()[0],
        )
        state, healthy = {}, False
        for _ in range(30):
            state = json.loads(
                run("inspect", name, "--format", "{{json .State}}").stdout
            )
            if not state["Running"]:
                break
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:18090/health", timeout=0.5
                ) as response:
                    healthy = response.status == 200
                if healthy:
                    break
            except OSError:
                time.sleep(0.2)
        s.record(
            {
                "kind": "algorithm_instance",
                "dictionary_sha256": digest(target.read_text(encoding="utf-8")),
                "healthy": healthy,
                "running": state.get("Running"),
                "exit_code": state.get("ExitCode"),
                "database": "N/A",
                "redis": "N/A",
            }
        )
        action(healthy, state)
    finally:
        # Explicitly owned temporary container, never shared project resources.
        subprocess.run(
            [*command, "rm", "-f", name],
            cwd=ROOT,
            check=False,
            capture_output=True,
            timeout=30,
        )


def register(s):
    def c115():
        for text, passed, hits in [
            ("一起去*死\u200b海旅行", True, []),
            ("你去*死\u200b", False, [{"word": "去死", "level": "HIGH"}]),
        ]:
            body = algorithm(s, text)
            assert body["passed"] is passed and body["hits"] == hits
        fingerprint = s.command(
            "exec",
            "-T",
            "algo",
            "python",
            "-c",
            "import hashlib,pathlib;print(hashlib.sha256("
            "pathlib.Path('app/data/words.json').read_bytes()).hexdigest())",
        )
        s.record(
            {
                "kind": "dictionary_identity",
                "source": "running container file",
                "sha256": fingerprint,
            }
        )

    s.run(115, c115)

    def c116():
        x, y = "去死海", "你去死"
        for text, passed in [
            (x + "," + x, True),
            (x + "," + y, False),
            (y + "," + x, False),
            (x + "," + y + "," + x, False),
            (y + "," + x + "," + y, False),
        ]:
            body = algorithm(s, text)
            assert body["passed"] is passed
            assert body["hits"] == (
                [] if passed else [{"word": "去死", "level": "HIGH"}]
            )

    s.run(116, c116)

    def c117():
        def check(healthy, state):
            assert healthy
            body = algorithm(s, "去死海", 18090)
            assert body["passed"] and body["hits"] == [
                {"word": "死海", "level": "MEDIUM"}
            ]

        instance(
            s,
            [
                {"word": "去死", "level": "HIGH", "allow_phrases": ["去死海"]},
                {"word": "死海", "level": "MEDIUM"},
            ],
            check,
        )

    s.run(117, c117)

    def c118():
        a = s.actor()

        def storage():
            return [
                int(s.sql(query))
                for query in [
                    f"SELECT COUNT(*) FROM treehole_identity WHERE user_id={a['id']}",
                    f"SELECT COUNT(*) FROM buddy_demand WHERE user_id={a['id']}",
                ]
            ]

        for text, expected in [("一起去死海旅行", 201), ("一起去死海旅行，煞笔", 422)]:
            before = storage()
            queue_before = int(s.redis("ZCARD", "treehole:burn_queue"))
            status, post, _ = s.post(a, text)
            assert status == expected
            if status == 201:
                pid = int(post["id"])
                assert s.sql(
                    f"SELECT user_id FROM treehole_identity WHERE post_id={pid}"
                ) == str(a["id"])
                assert s.redis("ZSCORE", "treehole:burn_queue", pid)
            body = s.need()
            body["remark"] = text
            status, _need, _ = s.buddy(a, body)
            assert status == expected
            after = storage()
            queue_after = int(s.redis("ZCARD", "treehole:burn_queue"))
            assert after == [v + (1 if expected == 201 else 0) for v in before]
            assert queue_after == queue_before + (1 if expected == 201 else 0)

    s.run(118, c118)

    def c119():
        benign = ["shabilist去死海", "myshabi去死海", "sha1bi去死海", "sha中文bi去死海"]
        for text in benign + ["shabi去死海", "SHǍBĪ去死海"]:
            body = algorithm(s, text)
            assert body["passed"] is (text in benign)
            assert body["hits"] == (
                [] if text in benign else [{"word": "傻逼", "level": "HIGH"}]
            )

    s.run(119, c119)

    def c120():
        for phrase in ["", "***", "正常内容", "去死", "长" * 129 + "去死"]:

            def rejected(healthy, state):
                assert (
                    not healthy
                    and state.get("Running") is False
                    and state["ExitCode"] != 0
                )

            instance(
                s,
                [{"word": "去死", "level": "HIGH", "allow_phrases": [phrase]}],
                rejected,
            )

        def positive(healthy, state):
            assert healthy and not algorithm(s, "去死", 18090)["passed"]

        instance(
            s,
            [{"word": "去死", "level": "HIGH", "allow_phrases": ["去死海"]}],
            positive,
        )

    s.run(120, c120)
