import hashlib
import json
import os
import re
from pathlib import Path

from pydantic import TypeAdapter
from pypinyin import lazy_pinyin

from app.models.dictionary import DictionaryEntry
from app.models.moderation import Hit, ModerationResponse
from app.services.normalization import normalize

_END = ""
_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


class ModerationService:
    def __init__(self, dictionary: Path | None = None):
        configured = os.environ.get("MODERATION_DICTIONARY_PATH")
        source = dictionary or (Path(configured) if configured else
                                Path(__file__).resolve().parents[1] / "data" / "words.json")
        self.trie: dict = {}
        self.pinyin: dict[str, tuple[str, str]] = {}
        dictionary_bytes = source.read_bytes()
        self.dictionary_sha256 = hashlib.sha256(dictionary_bytes).hexdigest()
        records = json.loads(dictionary_bytes.decode("utf-8-sig"))
        if not isinstance(records, list) or not records:
            raise ValueError("Dictionary must be a nonempty list")
        entries = TypeAdapter(list[DictionaryEntry]).validate_python(records)
        for record in entries:
            word, level = record.word, record.level
            for variant in [word, *record.aliases]:
                token = normalize(variant)
                node = self.trie
                for ch in token:
                    node = node.setdefault(ch, {})
                self._put(node, _END, (word, level))
            if record.pinyin:
                token = "".join(lazy_pinyin(word))
                self._put(self.pinyin, token, (word, level))

    @staticmethod
    def _put(mapping: dict, key: str, value: tuple[str, str]) -> None:
        if key in mapping and mapping[key] != value:
            raise ValueError("Conflicting dictionary variants")
        mapping[key] = value

    def check(self, text: str) -> ModerationResponse:
        normalized = normalize(text)
        found: dict[str, str] = {}
        for start in range(len(normalized)):
            node = self.trie
            for index in range(start, len(normalized)):
                ch = normalized[index]
                if ch not in node:
                    break
                node = node[ch]
                if _END in node:
                    word, level = node[_END]
                    found[word] = level
        # Match whole Latin runs, not arbitrary substrings (e.g. shabilist).
        # Han homophones use curated aliases; automatic phonetic folding overflags ordinary text.
        for token in re.findall(r"[a-z]+", normalized):
            if token in self.pinyin:
                word, level = self.pinyin[token]
                found[word] = level
        hits = [Hit(word=word, level=level) for word, level in sorted(
            found.items(), key=lambda item: (-_RANK[item[1]], item[0])
        )]
        return ModerationResponse(
            passed=all(hit.level != "HIGH" for hit in hits), normalized=normalized, hits=hits
        )
