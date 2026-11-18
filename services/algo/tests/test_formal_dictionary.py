import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.moderation import DEFAULT_DICTIONARY, ModerationService


def test_release_manifest_matches_frozen_default_and_does_not_invent_approval():
    manifest = json.loads(DEFAULT_DICTIONARY.with_name("moderation-v1.manifest.json").read_text(
        encoding="utf-8"))
    assert manifest["sha256"] == hashlib.sha256(DEFAULT_DICTIONARY.read_bytes()).hexdigest()
    assert manifest["entry_count"] == 46
    assert manifest["level_counts"] == {"HIGH": 22, "MEDIUM": 19, "LOW": 5}
    assert manifest["decision_policy"] == {"HIGH": "block", "MEDIUM": "allow", "LOW": "allow"}
    assert "await M1" in manifest["business_approval"]
    root = Path(__file__).resolve().parents[3]
    external = json.loads((root / "docs/qa/data/external/cold-test.v1.json").read_text(
        encoding="utf-8"))
    assert external["dictionary_frozen_sha256"] == manifest["sha256"]


@pytest.mark.parametrize("text", [
    "你个畜生", "狗-杂-种", "你不配活著", "見你一次打你一次", "nòng sǐ nǐ", "你这婊子",
])
def test_explicit_abuse_and_targeted_threats_are_blocked(text):
    assert not ModerationService().check(text).passed


@pytest.mark.parametrize("text", [
    "全家都支持我寻求心理咨询", "我想自杀，请陪我聊一会", "我患有抑郁症，想找人说话",
    "同性恋同学也应获得平等尊重", "杂种优势是遗传学概念", "操作系统课在三楼",
    "暑假去死海旅游", "白痴和弱智这类侮辱性用词不应随意使用", "垃圾分类和废物回收",
    "草泥马是一种网络称呼", "我对这个观点持不同意见", "我爷爷去世了，我很难受",
])
def test_identity_help_seeking_and_ordinary_contexts_are_not_blocked(text):
    assert ModerationService().check(text).passed


def test_nonblocking_levels_and_explicit_starter_rollback():
    service = ModerationService()
    assert service.check("白痴，混蛋，扯淡").passed
    assert {hit.level for hit in service.check("白痴，扯淡").hits} == {"MEDIUM", "LOW"}
    starter = ModerationService(DEFAULT_DICTIONARY.with_name("words.json"))
    assert starter.check("你不配活着").passed
    assert not service.check("你不配活着").passed


def test_http_header_attests_exact_dictionary_without_changing_json_contract():
    response = TestClient(app).post("/api/moderation/check", json={"text": "正常校园交流"})
    assert response.status_code == 200
    assert response.headers["X-Moderation-Dictionary-SHA256"] == hashlib.sha256(
        DEFAULT_DICTIONARY.read_bytes()).hexdigest()
    assert set(response.json()) == {"passed", "normalized", "hits"}
