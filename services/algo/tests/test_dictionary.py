import json

import pytest

from app.services.moderation import ModerationService


@pytest.mark.parametrize("entry", [
    {"word": 123, "level": "HIGH"}, {"word": "x", "level": "HIGH", "pinyin": "true"},
    {"word": "x", "level": "HIGH", "aliases": "abc"},
    {"word": "x", "level": "HIGH", "aliases": [123]},
    {"word": "x", "level": "HIGH", "extra": True},
    {"word": "a" * 65, "level": "HIGH"},
    {"word": "x", "level": "HIGH", "aliases": ["a" * 65]},
])
def test_dictionary_schema_is_strict(tmp_path, entry):
    path = tmp_path / "words.json"
    path.write_text(json.dumps([entry]), encoding="utf-8")
    with pytest.raises(ValueError):
        ModerationService(path)


def test_external_dictionary_configuration(tmp_path, monkeypatch):
    path = tmp_path / "reviewed-words.json"
    path.write_text(json.dumps([{"word": "测试词", "level": "HIGH"}]), encoding="utf-8")
    monkeypatch.setenv("MODERATION_DICTIONARY_PATH", str(path))
    service = ModerationService()
    assert service.check("测试词").passed is False
    # Replacement is explicit: starter terms aren't silently merged.
    assert service.check("傻逼").passed is True


def test_missing_configured_file_fails_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DICTIONARY_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError):
        ModerationService()
