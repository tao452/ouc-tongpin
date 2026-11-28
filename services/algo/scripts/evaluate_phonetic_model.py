"""Development-only phonetic reconstruction followed by local comment classification."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pypinyin import lazy_pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import ROOT, development, pcr, sha  # noqa: E402
from evaluate_comment_model import LocalModel, evaluate, safe_json, summarize  # noqa: E402
from evaluate_recall import source_sha  # noqa: E402

from app.services.moderation import ModerationService  # noqa: E402
from app.services.targeted_matching import latin_boundary  # noqa: E402


def grounded_hints(value, text):
    if (not isinstance(value, dict) or set(value) != {"replacements"}
            or not isinstance(value["replacements"], list) or len(value["replacements"]) > 4):
        raise ValueError("Invalid reconstruction output")
    hints, seen = [], set()
    for item in value["replacements"]:
        if (not isinstance(item, dict) or set(item) != {"source", "reading", "certainty"}
                or any(not isinstance(item[k], str) or not 1 <= len(item[k]) <= 32
                       for k in ["source", "reading"])
                or not item["source"].strip() or not item["reading"].strip()
                or not isinstance(item["certainty"], str)
                or item["certainty"] not in {"possible", "likely"}):
            raise ValueError("Invalid reconstruction hint")
        source = item["source"]
        start = text.find(source)
        while start >= 0 and not latin_boundary(text, start, start + len(source), source):
            start = text.find(source, start + 1)
        if start < 0:
            raise ValueError("Hint source absent or inside an English identifier")
        key = (start, source, item["reading"], item["certainty"])
        if key not in seen:
            seen.add(key)
            hints.append({**item, "span": [start, start + len(source)]})
    return hints


class PhoneticModel(LocalModel):
    def __init__(self, base_url, name, prompt, tokenizer, reconstruction, private_hints):
        super().__init__(base_url, name, prompt, tokenizer)
        self.reconstruction, self.private_hints = reconstruction, private_hints

    def predict(self, sample):
        messages = [dict(role="system", content=self.reconstruction["system"])]
        for example in self.reconstruction["examples"]:
            messages.append(dict(role="user", content=safe_json(dict(
                text=example["text"], pinyin=" ".join(lazy_pinyin(example["text"]))))))
            messages.append(dict(role="assistant", content=safe_json(
                dict(replacements=example["replacements"]))))
        messages.append(dict(role="user", content=safe_json(sample)))
        rendered = self.tokenizer.apply_chat_template(messages, tokenize=False,
                                                       add_generation_prompt=True,
                                                       enable_thinking=False)
        tokens = self.tokenizer(rendered, add_special_tokens=False)["input_ids"]
        if len(tokens) > 8192:
            raise ValueError("Reconstruction input exceeds token budget; no truncation")
        response = self.request("/api/generate", dict(
            model=self.name, prompt=rendered, raw=True, stream=False, keep_alive="2m",
            format=self.reconstruction["output_schema"], options=dict(
                temperature=0, seed=20261124, num_predict=256, num_ctx=8192, num_thread=4)))
        if response.get("model") != self.name or not response.get("done"):
            raise ValueError("Reconstruction identity or completion differs")
        hints = grounded_hints(json.loads(response["response"]), sample["text"])
        digest = hashlib.sha256(safe_json(hints).encode()).hexdigest()
        # Raw corpus-derived hints stay private. Public evidence uses hashes and counts.
        with self.private_hints.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(input_sha256=hashlib.sha256(
                sample["text"].encode()).hexdigest(), hints=hints), ensure_ascii=False) + "\n")
        classified = super().predict({**sample, "phonetic_hints": hints})
        return dict(**classified, hint_count=len(hints), hint_sha256=digest,
                    reconstruction_input_tokens=len(tokens),
                    reconstruction_output_tokens=response.get("eval_count"),
                    reconstruction_duration_ns=response.get("total_duration"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcr", required=True, type=Path)
    parser.add_argument("--tokenizer-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reconstruction", type=Path,
                        default=ROOT / "docs/qa/data/phonetic-reconstruction.v1.prompt.json")
    parser.add_argument("--classification", type=Path,
                        default=ROOT / "docs/qa/data/comment-classifier.v3.prompt.json")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.with_suffix(".hints.jsonl").exists():
            raise FileExistsError("Evidence already exists")
        # Reconstruction hints contain source substrings and must remain private.
        private_root = (ROOT / "qa-private").resolve()
        if not args.output.resolve().is_relative_to(private_root):
            raise ValueError("Run under qa-private; publish the sanitized final report separately")
        from transformers import AutoTokenizer
        reconstruction = json.loads(args.reconstruction.read_text(encoding="utf-8"))
        classification = json.loads(args.classification.read_text(encoding="utf-8"))
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_dir, local_files_only=True,
                                                   trust_remote_code=False)
        model = PhoneticModel("http://127.0.0.1:11434", args.model, classification, tokenizer,
                              reconstruction, args.output.with_suffix(".hints.jsonl"))
        dictionary = ROOT / "services/algo/app/data/moderation-v3_3-candidate.json"
        literal = ModerationService(dictionary)
        manifest = json.loads((ROOT / "docs/qa/data/external/pcr-test.v1.json").read_text(
            encoding="utf-8"))
        rows, exclusions = pcr(args.pcr, manifest)
        if exclusions:
            raise ValueError("No source row may disappear")
        for row in rows:
            row["cohort"] = "PCR"
        for version in ["v2", "v3"]:
            controls = development(ROOT / f"docs/qa/data/us24-development.{version}.jsonl")
            rows.extend(dict(id=f'{version}-{r["id"]}', text=r["text"], offensive=False,
                             cohort="controls") for r in controls if not r["expected_word"])
        policy = dict(model=model.name, model_digest=model.digest,
                      code_sha256=source_sha(Path(__file__)),
                      classification_code_sha256=source_sha(Path(__file__).with_name(
                          "evaluate_comment_model.py")),
                      reconstruction_prompt_sha256=sha(args.reconstruction),
                      classification_prompt_sha256=sha(args.classification),
                      runtime={p: importlib.metadata.version(p) for p in
                               ["transformers", "tokenizers", "pypinyin"]},
                      support_code_sha256={name: source_sha(Path(__file__).with_name(name))
                                           for name in ["evaluate_candidate.py",
                                                        "evaluate_recall.py",
                                                        "external_corpus.py"]},
                      development_sha256={version: sha(
                          ROOT / f"docs/qa/data/us24-development.{version}.jsonl")
                          for version in ["v2", "v3"]},
                      dictionary_sha256=literal.dictionary_sha256,
                      tokenizer_files={p.name: sha(p) for p in args.tokenizer_dir.iterdir()
                                       if p.is_file()},
                      engine_sha256={p.relative_to(ROOT).as_posix(): source_sha(p)
                                     for p in [
                                         *(ROOT / "services/algo/app/services").glob("*.py"),
                                         *(ROOT / "services/algo/app/models").glob("*.py")]},
                      dataset_sha256=sha(args.pcr), rows=len(rows), mask_context=True,
                      max_hints=4, max_hint_characters=32, max_input_tokens=8192,
                      reconstruction_output_tokens=256, classification_output_tokens=96,
                      seed=20261124, ollama_version=model.request("/api/version"),
                      phase="development_only", production_enabled=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.with_suffix(".policy.json").open("x", encoding="utf-8") as handle:
            json.dump(policy, handle, ensure_ascii=False, indent=2)
        predictions = evaluate(rows, model, literal, True, args.output.with_suffix(".rows.jsonl"))
        curves = summarize(predictions, classification["threshold_grid"])
        passed = any(v["development_gate_met"] for curve in curves.values() for v in curve.values())
        result = dict(executed_at_utc=datetime.now(UTC).isoformat(), policy=policy,
                      excluded_rows=0, predictions=predictions, thresholds=curves,
                      production_acceptance=False, m1_review="PENDING", m3_reproduction="PENDING")
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps(dict(count=len(rows), metric_gate_met=passed)))
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError, StopIteration):
        print("Phonetic development evaluation failed: model, source or output", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
