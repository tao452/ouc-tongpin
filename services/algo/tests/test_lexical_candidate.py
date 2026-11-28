import json

import pytest

from app.services.moderation import STARTER_DICTIONARY, ModerationService
from scripts.evaluate_candidate import sha
from scripts.evaluate_lexical import DATASET, DICTIONARY, PLAN, audit, git_lf_sha, main, run


def test_lexical_fixture_and_scope_probes_have_separate_accounting(tmp_path):
    report = run(tmp_path / "literal.json")
    assert report["literal_development_passed"]
    assert report["measured_lexical_rows"] == 1029
    assert report["semantic_scope_probes"] == 9
    assert report["total_rows"] == 1038
    for measured in report["metrics"].values():
        assert sum(measured["confusion_matrix"].values()) == 1029
    assert not report["production_acceptance"]
    assert report["independent_evaluation"] == "NOT_RUN"
    assert not ({r["id"] for r in report["scope_probes"]}
                & {r["id"] for r in report["trace"]})


def test_word_matches_survive_subject_changes_without_sentence_enumeration():
    service = ModerationService(DICTIONARY)
    for text in ["他真是贱人", "她根本就是个蠢货", "这个人真是狗东西"]:
        response = service.check(text)
        assert response.passed  # 沿用MEDIUM放行口径，不能把命中自动改为阻断。
        assert response.hits
    for text in ["打卡", "杀菌", "死循环", "打断点调试", "脑瘫康复训练",
                 "智障人士支持", "公狗和母狗", "这是一个小丑演员", "这个方案一无是处"]:
        assert not service.check(text).hits


def test_local_exemptions_do_not_hide_attacks_before_or_after_them():
    service = ModerationService(DICTIONARY)
    assert not service.check("草泥马是羊驼的网络称呼").hits
    assert not service.check("我在抄你码，稍后一起调试").hits
    for text in ["草泥马是羊驼，操你妈", "操你妈，草泥马是羊驼",
                 "举报：“傻逼”，请处理。操你妈"]:
        assert not service.check(text).passed
    assert not service.check("你这2B铅笔很好用").hits
    response = service.check("你这2B铅笔很好用，你这个2B")
    assert response.passed and any(hit.word == "二逼" for hit in response.hits)


def test_ambiguous_pinyin_and_identifiers_keep_their_boundaries():
    service = ModerationService(DICTIONARY)
    for text in ["fan tong", "chun lv", "nao zhong", "fan jian", "const sb = 1;",
                 "nmsl_client", "cnm_client", "tmd_config", "prefixshabisuffix"]:
        assert not service.check(text).hits
    assert any(h.word == "饭桶" for h in service.check("你个fan tong").hits)
    assert any(h.word == "操你妈" for h in service.check("你这个cnm").hits)


def test_homophone_target_cache_is_request_local_and_preserves_offsets(monkeypatch):
    import app.services.targeted_matching as targeted

    actual = targeted.has_target
    prefixes = []

    def counted(text, left):
        prefixes.append(text[max(0, left - targeted.TARGET_WINDOW):left])
        return actual(text, left)

    monkeypatch.setattr(targeted, "has_target", counted)
    trie = {"sha": {"bi": {"": ("傻逼", "HIGH")}}}
    text = "你这个沙比。" * 80
    result = list(targeted.homophone_spans(text, trie, lambda: None))
    assert len(result) == 80
    assert all(text[left:right] == "沙比" for left, right, _ in result)
    assert len(prefixes) == len(set(prefixes)) < len(text)
    prefixes.clear()
    assert not list(targeted.homophone_spans("沙比是普通人名", trie, lambda: None))
    assert prefixes  # 新请求重新建立缓存，不携带上一条请求的判断。


def test_default_and_historical_rollback_dictionaries_remain_available(monkeypatch):
    monkeypatch.delenv("MODERATION_DICTIONARY_PATH", raising=False)
    assert ModerationService().dictionary_sha256 == sha(STARTER_DICTIONARY)
    old = ModerationService(DICTIONARY.with_name("moderation-v3_13-candidate.json"))
    new = ModerationService(DICTIONARY)
    assert not old.check("我要打断你的腿").passed
    assert not new.check("我要打断你的腿").hits  # 本版不枚举整句，不能将此记录成语义真阴性。
    assert not old.check("你个婊子").passed
    response = new.check("你个婊子")
    assert response.passed and any(h.word == "婊子" and h.level == "MEDIUM"
                                   for h in response.hits)
    assert audit()["historical_rules_accounted"] == 132


def test_audit_rejects_source_grade_changes_and_invented_approval(tmp_path):
    data = json.loads(DICTIONARY.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    dictionary, plan_path = tmp_path / "dictionary.json", tmp_path / "plan.json"
    data[0]["level"] = "LOW"
    dictionary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    plan["dictionary_sha256"] = sha(dictionary)
    plan["entries"][0]["suggested_level"] = "LOW"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="source severity"):
        audit(dictionary, plan_path)
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan["entries"][0]["m1_status"] = "APPROVED"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="invent M1"):
        audit(DICTIONARY, plan_path)


def test_audit_rejects_missing_dispositions_and_bad_candidate_hash(tmp_path):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_path = tmp_path / "plan.json"
    plan["old_dispositions"].pop()
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one disposition"):
        audit(DICTIONARY, plan_path)
    plan["dictionary_sha256"] = "0" * 64
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="hash differs"):
        audit(DICTIONARY, plan_path)


def test_cli_rejects_remote_services_and_evidence_overwrite(tmp_path):
    output = tmp_path / "evidence.json"
    assert main(["--output", str(output), "--base-url", "https://example.com"]) == 2
    output.write_text("preserved", encoding="utf-8")
    assert main(["--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "preserved"
    assert sha(DATASET)


def test_rollback_content_hash_accepts_line_endings_but_rejects_changed_values(tmp_path):
    unix, windows, altered = (tmp_path / name for name in ["lf.json", "crlf.json", "changed.json"])
    original = '[\n  {"word":"傻逼","level":"HIGH"}\n]\n'.encode()
    unix.write_bytes(original)
    windows.write_bytes(original.replace(b"\n", b"\r\n"))
    altered.write_bytes(original.replace(b"HIGH", b"LOW"))
    assert sha(unix) != sha(windows)
    assert git_lf_sha(unix) == git_lf_sha(windows)
    assert git_lf_sha(unix) != git_lf_sha(altered)
