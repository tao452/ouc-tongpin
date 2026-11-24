import hashlib
import json
import os
import re
import time
import unicodedata
from pathlib import Path

from pydantic import TypeAdapter
from pypinyin import Style, pinyin

from app.models.dictionary import DictionaryEntry
from app.models.moderation import Hit, ModerationResponse
from app.services.moderation_context import context_spans, has_clause_boundary
from app.services.normalization import canonicalize, normalize
from app.services.pronunciation import (
    MAX_PINYIN_LENGTH,
    numeric_tone_pattern,
    numeric_tone_prefixed_patterns,
    pronunciation_keys,
)
from app.services.targeted_matching import (
    TARGET_WINDOW,
    has_target,
    homophone_spans,
    is_target_prefix,
    latin_boundary,
)

_END = ""
_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
DEFAULT_DICTIONARY = Path(__file__).resolve().parents[1] / "data" / "moderation-v1.json"
CANDIDATE_DICTIONARY = DEFAULT_DICTIONARY.with_name("moderation-v2-candidate.json")
RECALL_DICTIONARY = DEFAULT_DICTIONARY.with_name("moderation-v3-candidate.json")
STARTER_DICTIONARY = DEFAULT_DICTIONARY.with_name("words.json")
MATCH_BUDGET_SECONDS = 0.05
MAX_INPUT_LENGTH = 2000
MAX_TOKEN_PARTS = 64


class ModerationInputError(ValueError):
    """Input contract violation, distinct from internal dictionary/service faults."""


class ModerationService:
    def __init__(self, dictionary: Path | None = None):
        configured = os.environ.get("MODERATION_DICTIONARY_PATH")
        source = dictionary or (Path(configured) if configured else STARTER_DICTIONARY)
        self.trie: dict = {}
        self.pinyin: dict[str, tuple[str, str]] = {}
        self.joinable_pinyin: set[str] = set()
        self.numeric_tones: list[tuple[re.Pattern, str, str]] = []
        self.numeric_prefixes: dict[re.Pattern, str] = {}
        self.self_context_variants: dict[str, set[str]] = {
            word: set() for word in ["去死", "傻逼", "废物", "杀了你", "弄死你", "捅死你",
                                    "打死你", "砍死你", "掐死你", "泼你硫酸", "捅你一刀",
                                    "骚扰到你退学", "堵到你不敢出门"]}
        self.allow_phrases: dict[str, list[str]] = {}
        self.variants: set[str] = set()
        self.pinyin_allow: dict[str, list[re.Pattern]] = {}
        self.targeted_variants: set[tuple[str, str]] = set()
        self.targeted_words: set[str] = set()
        self.homophones: dict = {}
        dictionary_bytes = source.read_bytes()
        self.dictionary_sha256 = hashlib.sha256(dictionary_bytes).hexdigest()
        records = json.loads(dictionary_bytes.decode("utf-8-sig"))
        if not isinstance(records, list) or not 1 <= len(records) <= 512:
            raise ValueError("Dictionary must be a nonempty list")
        entries = TypeAdapter(list[DictionaryEntry]).validate_python(records)
        seen_words = set()
        for record in entries:
            word, level = record.word, record.level
            if record.target_required:
                self.targeted_words.add(word)
            if normalize(word) in seen_words:
                raise ValueError("Duplicate dictionary word")
            seen_words.add(normalize(word))
            self.allow_phrases.setdefault(word, []).extend(
                normalize(phrase) for phrase in record.allow_phrases)
            for variant in [word, *record.aliases, *record.targeted_aliases]:
                token = normalize(variant)
                if word in self.self_context_variants:
                    self.self_context_variants[word].add(token)
                if record.target_required or variant in record.targeted_aliases:
                    self.targeted_variants.add((word, token))
                self.variants.add(token)
                node = self.trie
                for ch in token:
                    node = node.setdefault(ch, {})
                self._put(node, _END, (word, level))
            if record.pinyin:
                # Only actual phrase readings and numeric tones may be split/joined.
                # Explicit typo aliases are exact whole Latin tokens; joining parts
                # would silently invent additional unreviewed typo combinations.
                self.joinable_pinyin.update(pronunciation_keys(word, record.pinyin_readings))
                keys = pronunciation_keys(word, record.pinyin_readings, record.pinyin_aliases)
                if record.pinyin_tone_numbers:
                    for prefix, pattern in numeric_tone_prefixed_patterns(
                            word, record.pinyin_readings, record.pinyin_tone_readings):
                        self.numeric_tones.append((pattern, word, level))
                        self.numeric_prefixes[pattern] = prefix
                for phrase in record.pinyin_allow_phrases:
                    if (not re.fullmatch(r"[a-z]+(?: [a-z]+){1,15}", phrase)
                            or len(phrase) > 128
                            or not any(key in phrase.replace(" ", "")
                                       and len(phrase.replace(" ", "")) > len(key)
                                       for key in keys)):
                        raise ValueError("Pinyin exception must be a longer mapped phrase")
                    if record.pinyin_tone_numbers:
                        pattern = numeric_tone_pattern(phrase.split())
                    else:
                        expression = r"(?<![a-z0-9_])" + r"[^\w]*".join(phrase.split())
                        pattern = re.compile(expression + r"(?![a-z0-9_])")
                    self.pinyin_allow.setdefault(word, []).append(pattern)
                for token in keys:
                    if word in self.self_context_variants:
                        self.self_context_variants[word].add(token)
                    self._put(self.pinyin, token, (word, level))
                    self.variants.add(token)
            if record.hanzi_homophone:
                node = self.homophones
                for part in pinyin(word, style=Style.NORMAL, heteronym=False):
                    node = node.setdefault(part[0], {})
                self._put(node, _END, (word, level))
        self.pinyin_prefixes = {token[:end] for token in self.pinyin
                                for end in range(1, len(token) + 1)}

    @staticmethod
    def _put(mapping: dict, key: str, value: tuple[str, str]) -> None:
        if key in mapping and mapping[key] != value:
            raise ValueError("Conflicting dictionary variants")
        mapping[key] = value

    def check(self, text: str) -> ModerationResponse:
        if len(text) > MAX_INPUT_LENGTH:
            raise ModerationInputError("Moderation input exceeds 2000 characters")
        deadline = time.perf_counter() + MATCH_BUDGET_SECONDS

        def check_budget():
            if time.perf_counter() > deadline:
                raise TimeoutError("Moderation matching budget exceeded")

        quote_cache = {}  # Request-local; repeated quotation text is never retained globally.
        self_cache = {}

        def known_quote(quote):
            check_budget()
            if quote not in quote_cache:
                quote_cache[quote] = self.known_targeted_quote(quote, check_budget)
            return quote_cache[quote]

        def known_self_context(kind, quote):
            check_budget()
            key = (kind, quote)
            if key not in self_cache:
                self_cache[key] = self.self_context(kind, quote)
            return self_cache[key]

        canonical = canonicalize(text)
        # A necessary literal syllable check only removes impossible paths.
        # It never creates new pronunciation combinations or relaxes boundaries.
        numeric_candidates = [item for item in self.numeric_tones
                              if self.numeric_prefixes[item[0]] in canonical]
        check_budget()
        positions = [index for index, ch in enumerate(canonical)
                     if unicodedata.category(ch)[0] in {"L", "N"}]
        normalized = "".join(canonical[index] for index in positions)
        exemptions = context_spans(canonical, self.variants,
                                   (p for p, _, _ in numeric_candidates),
                                   known_quote, known_self_context)
        pinyin_allowed = {word: [match.span() for pattern in patterns
                                  for match in pattern.finditer(canonical)
                                  if not has_clause_boundary(match.group())]
                          for word, patterns in self.pinyin_allow.items()}

        def is_context(left, right):
            return any(start <= left and right <= end for start, end in exemptions)

        found: dict[str, str] = {}
        allowed_spans: dict[str, list[tuple[int, int]]] = {}
        for word, phrases in self.allow_phrases.items():
            check_budget()
            spans = allowed_spans.setdefault(word, [])
            for phrase in phrases:
                offset = normalized.find(phrase)
                while offset >= 0:
                    check_budget()
                    end = offset + len(phrase)
                    if not has_clause_boundary(canonical[positions[offset]:positions[end - 1] + 1]):
                        spans.append((offset, end))
                    offset = normalized.find(phrase, offset + 1)
        for start in range(len(normalized)):
            if start % 32 == 0:
                check_budget()
            node = self.trie
            for index in range(start, len(normalized)):
                ch = normalized[index]
                if ch not in node:
                    break
                node = node[ch]
                if _END in node:
                    word, level = node[_END]
                    left, right = positions[start], positions[index] + 1
                    variant = normalized[start:index + 1]
                    if (not latin_boundary(canonical, left, right, variant)
                            or ((word, variant) in self.targeted_variants
                                and not has_target(canonical, left))):
                        continue
                    if (not any(left <= start and index < right
                                for left, right in allowed_spans.get(word, []))
                            and not is_context(positions[start], positions[index] + 1)):
                        found[word] = level
        if self.homophones:
            for left, right, (word, level) in homophone_spans(
                    canonical, self.homophones, check_budget):
                if (not is_context(left, right)
                        and not any(positions[a] <= left and right <= positions[b - 1] + 1
                                    for a, b in allowed_spans.get(word, []))):
                    found[word] = level
        # Preserve whole Latin-token boundaries before removing separators. This detects
        # "say shabi now" and "sha bi", without treating "shabilist" as a match.
        tokens = list(re.finditer(r"(?<![a-z0-9_])[a-z0-9]+(?![a-z0-9_])", canonical))
        for start, first in enumerate(tokens):
            if start % 32 == 0:
                check_budget()
            token = ""
            previous_end = first.start()
            for end in range(start, min(len(tokens), start + MAX_TOKEN_PARTS)):
                segment = tokens[end]
                gap = canonical[previous_end:segment.start()]
                if (len(gap) > 8 or "_" in gap
                        or any(unicodedata.category(ch)[0] in {"L", "N"} for ch in gap)):
                    break
                token += segment.group()
                if len(token) > MAX_PINYIN_LENGTH or token not in self.pinyin_prefixes:
                    break
                if token in self.pinyin:
                    word, level = self.pinyin[token]
                    if ((end == start or token in self.joinable_pinyin)
                            and (word not in self.targeted_words
                                 or has_target(canonical, first.start()))
                            and not is_context(first.start(), segment.end())
                            and not any(left <= first.start() and segment.end() <= right
                                        for left, right in pinyin_allowed.get(word, []))):
                        found[word] = level
                previous_end = segment.end()
        for index, (pattern, word, level) in enumerate(numeric_candidates):
            if index % 16 == 0:
                check_budget()
            for match in pattern.finditer(canonical):
                if ((word not in self.targeted_words or has_target(canonical, match.start()))
                        and not is_context(match.start(), match.end())
                        and not any(left <= match.start() and match.end() <= right
                                    for left, right in pinyin_allowed.get(word, []))):
                    found[word] = level
        check_budget()
        hits = [Hit(word=word, level=level) for word, level in sorted(
            found.items(), key=lambda item: (-_RANK[item[1]], item[0])
        )]
        return ModerationResponse(
            passed=all(hit.level != "HIGH" for hit in hits), normalized=normalized, hits=hits
        )

    def known_targeted_quote(self, quote, check_budget=lambda: None):
        """Only a full finite target prefix plus one known token, inside a template."""
        # This reversal is still an attack when unquoted. Inside an existing
        # report template, recognize only a complete registered denial token.
        if quote.startswith("我不会") and quote.endswith("才怪"):
            check_budget()
            if self.self_context("denial", quote[3:-2].strip()):
                return True
        for left in range(1, min(TARGET_WINDOW, len(quote) - 1) + 1):
            check_budget()
            if not is_target_prefix(quote[:left]):
                continue
            token = quote[left:].strip()
            if (normalize(token) in self.variants
                    or any(p.fullmatch(token) for p, _, _ in self.numeric_tones)):
                return True
        return any(right == len(quote) and is_target_prefix(quote[:left])
                   for left, right, _ in homophone_spans(quote, self.homophones, check_budget))

    def self_context(self, kind, quote):
        """Finite first-person forms, never a global exemption for asking for help."""
        words = {"harm": {"去死"}, "blame": {"傻逼", "废物"},
                 "denial": {"杀了你", "弄死你", "捅死你", "打死你", "砍死你", "掐死你",
                            "泼你硫酸", "捅你一刀", "骚扰到你退学", "堵到你不敢出门"}}
        words = words.get(kind, set())
        token = normalize(quote)
        return (any(token in self.self_context_variants[word] for word in words)
                or any(word in words and pattern.fullmatch(quote)
                       for pattern, word, _ in self.numeric_tones))
