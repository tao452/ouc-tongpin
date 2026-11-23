"""Generate the frozen US-12 synthetic fixture; refuse to overwrite prior evidence."""

import argparse
import gzip
import hashlib
import io
import json
import platform
import random
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/algo"))
from match.features import features  # noqa: E402
from match.models import Candidate, Profile  # noqa: E402
from match.scorer import DEFAULT_CONFIG  # noqa: E402

SEED = 20261124
TOPICS = ["跑步", "摄影", "电影", "阅读", "Python", "C++", "游泳", "音乐", "羽毛球", "绘画"]


def relevance(values):
    # Independent threshold rule, not the weighted score. It is synthetic and awaits M1 review.
    if values["time_jaccard"] == 0 or values["distance_m"] is None or values["distance_m"] > 15000:
        return 0
    good = [values["distance_m"] <= 5000, values["time_jaccard"] >= .25,
            values["emotion_similarity"] >= .5, values["interest_jaccard"] >= .25]
    return 3 if all(good) else 2 if sum(good) >= 2 else 1 if any(good) else 0


def generate(seed=SEED, query_count=100, candidates_per_query=50):
    rng = random.Random(seed)
    order = list(range(query_count))
    rng.shuffle(order)
    split = {i: "train" if j < query_count * .6 else "development" if j < query_count * .8
             else "test" for j, i in enumerate(order)}
    rows = []
    for number in range(query_count):
        qid = f"SYN-Q{number:03}"
        instant = datetime(2026, 12, 1, 9, tzinfo=UTC) + timedelta(days=number % 28)
        emotion_index = rng.randrange(6)
        vector = [float(i == emotion_index) for i in range(6)]
        latitude, longitude = round(rng.uniform(-60, 60), 6), round(rng.uniform(-150, 150), 6)
        query = {"emotion_vector": vector, "interests": rng.sample(TOPICS, 3),
                 "availability": [{"start": instant.isoformat(),
                                   "end": (instant + timedelta(hours=2)).isoformat()}],
                 "location": {"lat": latitude, "lng": longitude}}
        cohort = {0: "missing_emotion", 1: "missing_interests", 2: "missing_time",
                  3: "missing_location"}.get(number % 10, "complete")
        if cohort != "complete":
            field = {"missing_emotion": "emotion_vector", "missing_interests": "interests",
                     "missing_time": "availability", "missing_location": "location"}[cohort]
            query[field] = [] if field in {"interests", "availability"} else None
        model = Profile.model_validate(query)
        for index in range(candidates_per_query):
            cid = f"SYN-Q{number:03}-C{index:03}"
            category = rng.randrange(6)
            candidate_vector = [float(i == category) for i in range(6)]
            start = instant + timedelta(hours=rng.randrange(-3, 5))
            candidate = {"id": cid, "emotion_vector": candidate_vector,
                         "interests": rng.sample(TOPICS, rng.randrange(0, 6)),
                         "availability": [{"start": start.isoformat(), "end": (start + timedelta(
                             hours=rng.randrange(1, 4))).isoformat()}],
                         "location": {"lat": round(latitude + rng.uniform(-.2, .2), 6),
                                      "lng": round(longitude + rng.uniform(-.25, .25), 6)}}
            values = features(model, Candidate.model_validate(candidate))
            rows.append(dict(query_id=qid, split=split[number], cohort=cohort,
                             query=query, candidate=candidate, relevance=relevance(values)))
    return rows


def encode(rows):
    raw = ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                     for row in rows) + "\n").encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as output:
        output.write(raw)
    return raw, buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/algorithms/data/us12-synthetic.v1.jsonl.gz")
    args = parser.parse_args()
    manifest = args.output.with_name(args.output.name.replace(".jsonl.gz", ".manifest.json"))
    if args.output.exists() or manifest.exists() or manifest == args.output:
        parser.error("Output/manifest already exists; use a new dataset version")
    rows = generate()
    raw, packed = encode(rows)
    assert len(rows) == 5000 and len({r["candidate"]["id"] for r in rows}) == 5000
    meta = {"dataset": "us12-synthetic-v1", "seed": SEED, "rows": 5000, "queries": 100,
            "split_rows": dict(Counter(row["split"] for row in rows)),
            "cohort_rows": dict(Counter(row["cohort"] for row in rows)),
            "relevance_counts": dict(Counter(row["relevance"] for row in rows)),
            "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
            "gzip_sha256": hashlib.sha256(packed).hexdigest(), "gzip_bytes": len(packed),
            "python": platform.python_version(),
            "labels": "M6 synthetic threshold rule; PENDING M1",
            "source_commit_before_generation": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "weights_sha256": hashlib.sha256(DEFAULT_CONFIG.read_bytes()).hexdigest(),
            "protocol_sha256": hashlib.sha256((ROOT / "docs/algorithms/US12-W5W6-特征与评估方案.md")
                                                .read_bytes()).hexdigest(),
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "feature_code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                    for name in ["services/algo/match/features.py",
                                                 "services/algo/match/models.py"]},
            "excluded_rows": 0, "business_acceptance": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(packed)
    manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
