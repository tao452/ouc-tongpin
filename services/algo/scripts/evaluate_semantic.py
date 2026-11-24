"""Offline semantic baseline, independent of S1 decisions and service dependencies.

Supply a pinned local safetensors model and dataset manifest. No remote model code,
automatic download, external inference call, dataset filtering or runtime deployment.
"""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import development, sha  # noqa: E402
from evaluate_dataset import validate_output_path  # noqa: E402
from evaluate_recall import load_external, source_sha  # noqa: E402
from external_corpus import metrics, record  # noqa: E402

MODEL_FILES = {"README.md", "config.json", "vocab.txt", "tokenizer_config.json",
               "special_tokens_map.json", "model.safetensors"}


def verify_model(directory, manifest):
    if (set(manifest["files"]) != MODEL_FILES or manifest.get("trust_remote_code") is not False
            or manifest.get("revision") != "614c097a485910d28beb75f60d90c61e3082b518"):
        raise ValueError("Unexpected model or manifest")
    for name, spec in manifest["files"].items():
        path = directory / name
        if path.stat().st_size != spec["bytes"] or sha(path) != spec["sha256"]:
            raise ValueError("Model bytes differ")


def summarize(rows, threshold):
    counts = dict(tp=0, fp=0, fn=0, tn=0)
    for row in rows:
        record(counts, row["probability"] >= threshold, bool(row["label"]))
    return metrics(counts)


def run(dataset, model_dir, model_manifest, output, manifest_path=None, thresholds=(0.5,)):
    model_spec = json.loads(model_manifest.read_text(encoding="utf-8"))
    verify_model(model_dir, model_spec)
    if not thresholds or any(not 0 < t < 1 for t in thresholds):
        raise ValueError("Invalid thresholds")
    inputs = [dataset, model_manifest, Path(__file__), *[model_dir / p for p in MODEL_FILES]]
    validate_output_path(output, inputs)
    if output.exists():
        raise FileExistsError("Evidence already exists")
    if manifest_path:
        spec = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = load_external(dataset, spec)
    else:
        rows = development(dataset)
        for row in rows:
            row["offensive"] = bool(row["expected_word"])
    # Optional heavy dependencies are loaded only by this offline command.
    import torch
    from transformers import BertForSequenceClassification, BertTokenizer

    torch.set_num_threads(6)
    tokenizer = BertTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = BertForSequenceClassification.from_pretrained(
        str(model_dir), local_files_only=True, use_safetensors=True).eval()
    predictions, window_count, elapsed = [], 0, 0.0
    for offset in range(0, len(rows), 16):
        batch = rows[offset:offset + 16]
        chunks, owners = [], []
        for index, row in enumerate(batch):
            for start in range(0, len(row["text"]), 384):
                chunks.append(row["text"][start:start + 448])
                owners.append(index)
        maxima = [0.0] * len(batch)
        for start in range(0, len(chunks), 16):
            tokens = tokenizer(chunks[start:start + 16], return_tensors="pt",
                               padding=True, truncation=False)
            if tokens["input_ids"].shape[1] > 512:
                raise ValueError("Tokenizer expansion exceeded model limit")
            began = time.perf_counter()
            with torch.inference_mode():
                probs = model(**tokens).logits.softmax(-1)[:, 1].tolist()
            elapsed += time.perf_counter() - began
            for index, probability in zip(owners[start:start + 16], probs, strict=True):
                maxima[index] = max(maxima[index], probability)
        window_count += len(chunks)
        predictions.extend(dict(id=row["id"], label=int(row["offensive"]), probability=p,
                                text_sha256=hashlib.sha256(row["text"].encode()).hexdigest())
                           for row, p in zip(batch, maxima, strict=True))
    result = dict(executed_at_utc=datetime.now(UTC).isoformat(), scope="offline_semantic_baseline",
                  model_manifest=model_spec, dataset_sha256=sha(dataset), count=len(rows),
                  code_sha256=source_sha(Path(__file__)), excluded_rows=0, windows=window_count,
                  inference_seconds=elapsed, runtime={p: importlib.metadata.version(p) for p in
                  ["torch", "transformers", "tokenizers", "safetensors", "numpy"]},
                  production_enabled=False, production_acceptance=False,
                  thresholds={str(t): summarize(predictions, t) for t in thresholds},
                  predictions=predictions)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, action="append")
    args = parser.parse_args(argv)
    try:
        result = run(args.dataset, args.model_dir, args.model_manifest, args.output,
                     args.manifest, args.threshold or (0.5,))
    except (ImportError, ValueError, OSError, KeyError, TypeError):
        print("Offline evaluation failed: model, dependencies, source or output", file=sys.stderr)
        return 2
    print(json.dumps({"count": result["count"], "thresholds": result["thresholds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
