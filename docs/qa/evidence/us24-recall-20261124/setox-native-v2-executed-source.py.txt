"""Measure a local SeTox model's native labels without executing model tools."""

import argparse
import importlib.metadata
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_candidate import ROOT, development, pcr, sha  # noqa: E402
from evaluate_comment_model import LocalModel, evaluate, safe_json, summarize  # noqa: E402
from evaluate_recall import source_sha  # noqa: E402

from app.services.moderation import ModerationService  # noqa: E402

CATEGORIES = {"贬损攻击", "成人内容", "违法犯罪", "违背道德", "敏感话题"}
CATEGORY_ALIASES = {"辱骂攻击": "贬损攻击"}


def parse_native(response):
    if not isinstance(response, str) or len(response) > 4096 or "<tool_call>" in response:
        raise ValueError("Invalid native response; no tool calls are executed")
    lines = response.strip().splitlines()
    if not lines or lines[0].strip() not in {"正常内容", "不安全内容"}:
        raise ValueError("Native label must be the first complete line")
    label = lines[0].strip()
    if any(line.strip() in {"正常内容", "不安全内容"} for line in lines[1:]):
        raise ValueError("Repeated or conflicting native label")
    categories = re.findall(r"^风险类别[：:]\s*([^\r\n]+)", response.strip(), re.MULTILINE)
    if label == "正常内容":
        if categories:
            raise ValueError("Normal label with unsafe category")
        return dict(native_unsafe=False, native_category=None, offense_score=0, crisis_hint=False)
    if len(categories) != 1:
        raise ValueError("Unsafe category must be one registered native category")
    raw_category = categories[0].strip()
    category = CATEGORY_ALIASES.get(raw_category, raw_category)
    if category not in CATEGORIES:
        raise ValueError("Unsafe category must be one registered native category")
    return dict(native_unsafe=True, native_category=category,
                native_category_raw=raw_category,
                offense_score=100 if category == "贬损攻击" else 0, crisis_hint=False)


class NativeModel(LocalModel):
    def predict(self, sample):
        messages = [dict(role="system", content=self.prompt["system"]),
                    dict(role="user", content=self.prompt["user_template"].replace(
                        "{sentence}", safe_json(sample["text"])))]
        rendered = self.tokenizer.apply_chat_template(messages, tokenize=False,
                                                       add_generation_prompt=True)
        tokens = self.tokenizer(rendered, add_special_tokens=False)["input_ids"]
        if len(tokens) > self.prompt["generation"]["num_ctx"]:
            raise ValueError("Input budget exceeded; no truncation")
        result = self.request("/api/generate", dict(
            model=self.name, prompt=rendered, raw=True, stream=False, keep_alive="2m",
            options=self.prompt["generation"]))
        if not result.get("done") or result.get("model") != self.name:
            raise ValueError("Incomplete or different model response")
        parsed = parse_native(result["response"])
        return dict(**parsed, input_tokens=len(tokens), output_tokens=result.get("eval_count"),
                    duration_ns=result.get("total_duration"))


def summarize_native(rows):
    # The native binary risk task includes categories outside the offense task.
    attack = summarize(rows, [1])
    unsafe_rows = [{**r, "offense_score": 100 if r.get("native_unsafe") else 0} for r in rows]
    return dict(native_attack=attack, native_all_unsafe=summarize(unsafe_rows, [1]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcr", required=True, type=Path)
    parser.add_argument("--tokenizer-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", type=Path,
                        default=ROOT / "docs/qa/data/setox-native.v1.prompt.json")
    parser.add_argument("--dictionary", type=Path,
                        default=ROOT / "services/algo/app/data/moderation-v3_3-candidate.json")
    parser.add_argument("--mask-context", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError("Evidence already exists")
        from transformers import AutoTokenizer
        prompt = json.loads(args.prompt.read_text(encoding="utf-8"))
        tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer_dir), local_files_only=True,
                                                   trust_remote_code=False)
        model = NativeModel("http://127.0.0.1:11434", args.model, prompt, tokenizer)
        literal = ModerationService(args.dictionary)
        manifest = json.loads((ROOT / "docs/qa/data/external/pcr-test.v1.json").read_text(
            encoding="utf-8"))
        rows, exclusions = pcr(args.pcr, manifest)
        if exclusions:
            raise ValueError("Development rows must not be removed")
        for row in rows:
            row["cohort"] = "PCR"
        control_sources = {}
        for version in ["v2", "v3"]:
            path = ROOT / f"docs/qa/data/us24-development.{version}.jsonl"
            controls = development(path)
            control_sources[version] = sha(path)
            rows.extend(dict(id=f'{version}-{r["id"]}', text=r["text"], offensive=False,
                             cohort="controls") for r in controls if not r["expected_word"])
        policy = dict(model=args.model, model_digest=model.digest, prompt_sha256=sha(args.prompt),
                      dictionary_sha256=literal.dictionary_sha256, mask_context=args.mask_context,
                      code_sha256=source_sha(Path(__file__)),
                      helper_sha256=source_sha(Path(__file__).with_name("evaluate_comment_model.py")),
                      engine_sha256={p.relative_to(ROOT).as_posix(): source_sha(p)
                                     for p in (ROOT / "services/algo/app/services").glob("*.py")},
                      tokenizer_files={p.name: sha(p) for p in args.tokenizer_dir.iterdir()
                                       if p.is_file() and p.suffix != ".safetensors"},
                      runtime={p: importlib.metadata.version(p) for p in
                               ["transformers", "tokenizers", "pypinyin"]},
                      ollama_version=model.request("/api/version"), tools_executed=0,
                      native_category_aliases=CATEGORY_ALIASES,
                      inference="loopback only; research model; no S1 level assignment",
                      production_enabled=False)
        provenance = dict(phase="development_only", rows=len(rows),
                          dataset_sha256=sha(args.pcr), controls_sha256=control_sources)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.with_suffix(".policy.json").open("x", encoding="utf-8") as handle:
            json.dump(dict(pipeline=policy, provenance=provenance), handle,
                      ensure_ascii=False, indent=2)
        predictions = evaluate(rows, model, literal, args.mask_context,
                               args.output.with_suffix(".rows.jsonl"))
        measured = summarize_native(predictions)
        passed = measured["native_attack"]["literal_or_model"]["1"]["development_gate_met"]
        result = dict(executed_at_utc=datetime.now(UTC).isoformat(), policy=policy,
                      provenance=provenance, excluded_rows=0, predictions=predictions,
                      metrics=measured, production_acceptance=False)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(json.dumps(dict(count=len(rows), metric_gate_met=passed)))
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError, StopIteration):
        print("SeTox evaluation failed: local model, source or output", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
