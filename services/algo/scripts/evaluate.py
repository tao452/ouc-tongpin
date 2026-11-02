"""Measure only the repository's developer regression fixture; no population accuracy claim."""
import json
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.moderation import ModerationService  # noqa: E402

service = ModerationService()
samples = [
    ("傻逼", False), ("傻 逼", False), ("傻必", False), ("煞笔", False),
    ("ＳＨＡＢＩ", False), ("s.h.a.b.i", False), ("操你媽", False), ("去-死", False),
    ("一起复习", True), ("垃圾分类", True), ("学习Python", True), ("需要帮助", True),
    ("shabilist", True), ("铅笔放在沙发旁", True), ("圖書館有空位", True), ("草泥马", True),
]
correct = sum(service.check(text).passed == expected for text, expected in samples)
durations = []
long_text = "今天一起去图书馆复习。" * 180
for _ in range(100):
    service.check(long_text)
for _ in range(1000):
    started = time.perf_counter()
    service.check(long_text)
    durations.append((time.perf_counter() - started) * 1000)
result = {
    "scope": "developer regression examples; not an independently annotated evaluation set",
    "python": platform.python_version(), "platform": platform.platform(),
    "examples": len(samples), "correct": correct,
    "benchmark": {"characters": len(long_text), "iterations": len(durations),
                  "median_ms": statistics.median(durations),
                  "p95_ms": sorted(durations)[949]},
    "limitations": "Single process, warm cache; not HTTP latency, concurrency or production recall",
}
print(json.dumps(result, ensure_ascii=False, indent=2))
