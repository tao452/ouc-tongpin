"""按有界的明确前缀判断攻击对象，不推断一般语义意图。"""

import re
import unicodedata

from pypinyin import Style, pinyin

TARGET_WINDOW = 16
_TARGET = re.compile(
    r"(?:你们?|他们?|她们?|这人|那人|楼主|博主|室友|同学|有些人)"
    r"(?:真|就|是|个|这|种|死|太|纯|小|老|臭|破|还|一|的|只|条|像|简直|就是){0,8}$"
)
_HANZI = re.compile(r"[\u3400-\u9fff]+")


def has_target(text, left):
    return _TARGET.search(text[max(0, left - TARGET_WINDOW):left]) is not None


def is_target_prefix(prefix):
    return len(prefix) <= TARGET_WINDOW and _TARGET.fullmatch(prefix) is not None


def _identifier_letter(ch):
    if ch.isascii():
        return ch.isalnum()
    if "\u3400" <= ch <= "\u9fff" or unicodedata.category(ch)[0] not in {"L", "N"}:
        return False
    # 中文及扩展汉字可以紧邻拼音词，不视为英文标识符的一部分。
    return not unicodedata.name(ch, "").startswith(
        ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH"))


def latin_boundary(text, left, right, variant):
    """拉丁字母及已登记的视觉别名保留Unicode标识符边界。"""
    return (not (_identifier_letter(variant[0]) and left
                 and (text[left - 1] == "_" or _identifier_letter(text[left - 1])))
            and not (_identifier_letter(variant[-1]) and right < len(text)
                     and (text[right] == "_" or _identifier_letter(text[right]))))


def homophone_spans(text, trie, check_budget):
    """每字只取一个上下文读音，不做多音字笛卡尔积或模糊编辑。

    每段汉字保持一字一音节，遍历由编译后的词语树限定在最多16音节；不跨标点拼接。
    """
    reading_cache = {}  # 读音缓存仅在本次请求内有效，不跨请求保留用户文本。
    target_cache = {}  # 仅在本次请求内复用相同的定向前缀，避免重复执行正则判断。
    for run in _HANZI.finditer(text):
        check_budget()
        for start in range(len(run.group())):
            if start % 16 == 0:
                check_budget()
            left = run.start() + start
            prefix = text[max(0, left - TARGET_WINDOW):left]
            if prefix not in target_cache:
                target_cache[prefix] = has_target(prefix, len(prefix))
            if not target_cache[prefix]:
                continue
            # 只读取有长度上限的候选窗口，避免对整段2000字反复取音。
            window = run.group()[start:start + 16]
            if window not in reading_cache:
                reading_cache[window] = pinyin(window, style=Style.NORMAL, heteronym=False)
            readings = reading_cache[window]
            if len(readings) != len(window):
                continue
            syllables = [r[0] for r in readings]
            node = trie
            for end, syllable in enumerate(syllables):
                node = node.get(syllable)
                if node is None:
                    break
                if "" in node:
                    yield left, left + end + 1, node[""]
