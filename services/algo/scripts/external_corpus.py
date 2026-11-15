"""Fixed external labels and aggregate metrics; never expose comment text or identities."""

import csv
import hashlib
import io
import math
from collections import Counter


def load_corpus(path, manifest):
    raw = path.read_bytes()
    if len(raw) != manifest["bytes"] or hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Corpus hash differs from the pinned official test split")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    columns = ["", "split", "topic", "label", "fine-grained-label", "TEXT"]
    if reader.fieldnames != columns:
        raise ValueError("External CSV schema differs")
    records, exclusions, seen, duplicates = [], Counter(), set(), 0
    total = 0
    for row in reader:
        total += 1
        if (set(row) != set(columns) or any(value is None for value in row.values())
                or row["label"] not in {"0", "1"}
                or row["fine-grained-label"] not in {"0", "1", "2", "3"}):
            raise ValueError("External row has an invalid label or shape")
        text = row["TEXT"]
        if not text.strip():
            exclusions["blank"] += 1
            continue
        if len(text) > 2000:
            exclusions["over_2000_characters"] += 1
            continue
        duplicates += text in seen
        seen.add(text)
        records.append({"text": text, "offensive": row["label"] == "1",
                        "fine_label": row["fine-grained-label"]})
    if total != manifest["rows"] or not records:
        raise ValueError("External test rows differ or no eligible samples remain")
    return records, {"upstream_rows": total, "eligible_rows": len(records),
                     "excluded_rows": sum(exclusions.values()),
                     "exclusion_reasons": dict(exclusions), "duplicate_rows_kept": duplicates}


def wilson(successes, total):
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def metrics(counts):
    positives = counts["tp"] + counts["fn"]
    negatives = counts["tn"] + counts["fp"]
    predicted = counts["tp"] + counts["fp"]
    recall = counts["tp"] / positives if positives else None
    fpr = counts["fp"] / negatives if negatives else None
    return {"confusion_matrix": dict(counts), "offensive_samples": positives,
            "nonoffensive_samples": negatives, "recall": recall,
            "precision": counts["tp"] / predicted if predicted else None,
            "false_positive_rate": fpr,
            "recall_wilson95": wilson(counts["tp"], positives),
            "false_positive_rate_wilson95": wilson(counts["fp"], negatives),
            "broad_benchmark_thresholds_met": (
                recall is not None and fpr is not None and recall >= 0.95 and fpr < 0.02)}


def record(counts, predicted, offensive):
    key = ("tp" if offensive else "fp") if predicted else ("fn" if offensive else "tn")
    counts[key] += 1
