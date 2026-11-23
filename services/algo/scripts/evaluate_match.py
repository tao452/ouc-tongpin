"""Compare US-12 and pure-tag rankings on the sealed synthetic fixture."""

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import ndcg_score

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/algo"))
from match.features import interest_jaccard  # noqa: E402
from match.metrics import ndcg  # noqa: E402
from match.models import ScoreRequest  # noqa: E402
from match.scorer import Scorer  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(dataset, manifest_path):
    manifest = json.loads(manifest_path.read_bytes())
    if sha(dataset) != manifest["gzip_sha256"]:
        raise ValueError("Synthetic compressed dataset hash changed")
    raw = gzip.decompress(dataset.read_bytes())
    if hashlib.sha256(raw).hexdigest() != manifest["raw_sha256"]:
        raise ValueError("Synthetic raw dataset hash changed")
    for name, digest in manifest["feature_code_sha256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen feature/schema changed; create another experiment version")
    protocol = ROOT / "docs/algorithms/US12-W5W6-特征与评估方案.md"
    if sha(protocol) != manifest["protocol_sha256"]:
        raise ValueError("Frozen protocol changed")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    ids = [row["candidate"]["id"] for row in rows]
    if (len(rows) != manifest["rows"] or len(set(ids)) != len(ids)
            or any(type(row["relevance"]) is not int or not 0 <= row["relevance"] <= 3
                   or row["split"] not in {"train", "development", "test"} for row in rows)):
        raise ValueError("Changed labels, duplicate IDs or split accounting")
    return rows, manifest


def http_score(base_url, request, expected_sha):
    url = urlsplit(base_url)
    if (url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "algo"}
            or url.username or url.password or url.query or url.fragment
            or url.path not in {"", "/"}):
        raise ValueError("HTTP evaluation requires an owned local/internal scoring service")
    payload = urllib.request.Request(base_url.rstrip("/") + "/score", method="POST",
        data=json.dumps(request, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(payload, timeout=3) as response:
        body = response.read(131073)
        if len(body) > 131072 or response.headers.get("X-Score-Config-SHA256") != expected_sha:
            raise ValueError("Scoring response size or config fingerprint mismatch")
    result = json.loads(body)
    if result["config_sha256"] != expected_sha or result["fallback"] is not False:
        raise ValueError("Unexpected scoring version/fallback")
    return result


def evaluate(dataset, manifest_path, output, base_url=None):
    if output.exists() or output.resolve() in {dataset.resolve(), manifest_path.resolve()}:
        raise ValueError("Keep prior reports and input data; use a new output path")
    rows, manifest = load(dataset, manifest_path)
    scorer = Scorer()
    if scorer.sha256 != manifest["weights_sha256"]:
        raise ValueError("Frozen weights changed")
    frame = pd.DataFrame(rows)
    if frame.groupby("query_id")["split"].nunique().max() != 1:
        raise ValueError("A query leaked across splits")
    queries, timings = [], []
    for qid, group in frame.groupby("query_id", sort=True):
        first = group.iloc[0]
        if any(row != first["query"] for row in group["query"]):
            raise ValueError("One query ID has inconsistent profiles")
        candidates = group["candidate"].tolist()
        request = {"query": first["query"], "candidates": candidates}
        parsed = ScoreRequest.model_validate(request)
        started = time.perf_counter()
        result = (http_score(base_url, request, scorer.sha256) if base_url
                  else scorer.score(parsed))
        timings.append((time.perf_counter() - started) * 1000)
        values = {row["id"]: row["score"] for row in result["items"]}
        if len(result["items"]) != len(candidates) or set(values) != {c["id"] for c in candidates}:
            raise ValueError("Missing/duplicate prediction; no candidate may be excluded")
        predicted = [values[c["id"]] for c in candidates]
        baseline = [round(100 * interest_jaccard(first["query"]["interests"], c["interests"]), 6)
                    for c in candidates]
        labels = group["relevance"].tolist()
        weighted_ndcg, baseline_ndcg = ndcg(labels, predicted), ndcg(labels, baseline)
        for scores, actual in [(predicted, weighted_ndcg), (baseline, baseline_ndcg)]:
            expected = float(ndcg_score(np.array([labels]), np.array([scores]), k=10))
            if abs(actual - expected) > 1e-12:
                raise ValueError("NDCG disagrees with pinned scikit-learn reference")
        queries.append(dict(query_id=qid, split=first["split"], cohort=first["cohort"],
            candidates=len(candidates), zero_gain_query=not any(labels),
            weighted_ndcg_at_10=weighted_ndcg, tag_ndcg_at_10=baseline_ndcg))
    results = pd.DataFrame(queries)

    def groups(field):
        return {name: dict(queries=len(group), candidates=int(group["candidates"].sum()),
                    zero_gain_queries=int(group["zero_gain_query"].sum()),
                    weighted_ndcg_at_10=float(group["weighted_ndcg_at_10"].mean()),
                    tag_ndcg_at_10=float(group["tag_ndcg_at_10"].mean()))
                for name, group in results.groupby(field, sort=True)}

    report = dict(source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"],
                    cwd=ROOT, text=True).strip(), executed_at_utc=datetime.now(UTC).isoformat(),
        evaluation_completed=True, mode="http" if base_url else "function", rows=len(rows),
        queries=len(queries), excluded_rows=0, duplicate_candidate_ids_kept=0,
        dataset_sha256=manifest["raw_sha256"], compressed_sha256=manifest["gzip_sha256"],
        manifest_sha256=sha(manifest_path),
        input_validation_revision=manifest.get("input_validation_revision", "v1"),
        weights_sha256=scorer.sha256, feature_version=scorer.config.feature_version,
        metric="linear gain, tie-averaged NDCG@10; zero-gain queries included as0",
        split_metrics=groups("split"), cohort_metrics=groups("cohort"), query_results=queries,
        label_counts=dict(Counter(row["relevance"] for row in rows)),
        p95_ms=float(np.percentile(timings, 95)), max_ms=max(timings),
        reference_metric_crosschecks=len(queries) * 2,
        dependency_versions=dict(python=platform.python_version(), numpy=np.__version__,
                                  pandas=pd.__version__, sklearn=sklearn.__version__),
        semantic_scope="Synthetic threshold labels; no independent human match-quality acceptance",
        business_acceptance=False, m1_metric_review="PENDING", m3_reproduction="PENDING")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data = ROOT / "docs/algorithms/data"
    parser.add_argument("--dataset", type=Path, default=data / "us12-synthetic.v1.jsonl.gz")
    parser.add_argument("--manifest", type=Path,
                        default=data / "us12-synthetic.v1.validation-v1_1.manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url")
    args = parser.parse_args()
    result = evaluate(args.dataset, args.manifest, args.output, args.base_url)
    print(json.dumps(result["split_metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
