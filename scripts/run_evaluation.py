"""Evaluate the local Ollama orchestration prompt contracts on held-out data.

This is evaluation, not weight training. The training split supplies a small
few-shot calibration context; model parameters are never changed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "evaluation_data"
REPORT_PATH = ROOT / "EVALUATION_REPORT.md"
RESULTS_PATH = ROOT / "outputs" / "evaluation_results.json"


def read_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def read_parquet(path: Path, limit: int) -> list[dict[str, Any]]:
    table = pq.read_table(path).slice(0, limit)
    return table.to_pylist()


def parse_json_response(response: Any) -> dict[str, Any]:
    content = response.get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(match.group(0)) if match else {}


def classify(client: ollama.Client, model: str, prompt: str) -> dict[str, Any]:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": "Return only valid JSON. Do not explain outside JSON."},
            {"role": "user", "content": prompt},
        ],
        format="json",
    )
    return parse_json_response(response)


def few_shot(rows: list[dict[str, Any]], limit: int) -> str:
    return "\n".join(
        f"Example {index}: claim={row['claim']!r}; evidence={row['evidence']!r}; label={row['label']!r}"
        for index, row in enumerate(rows[:limit], 1)
    )


def score_labels(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    labels = sorted(set(expected) | set(predicted))
    correct = sum(actual == guess for actual, guess in zip(expected, predicted))
    per_label = {}
    for label in labels:
        tp = sum(actual == label and guess == label for actual, guess in zip(expected, predicted))
        fp = sum(actual != label and guess == label for actual, guess in zip(expected, predicted))
        fn = sum(actual == label and guess != label for actual, guess in zip(expected, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    macro_f1 = sum(item["f1"] for item in per_label.values()) / len(per_label) if per_label else 0.0
    return {"count": len(expected), "accuracy": correct / len(expected) if expected else 0.0, "macro_f1": macro_f1, "per_label": per_label}


def score_multilabel(expected: list[list[int]], predicted: list[list[int]]) -> dict[str, Any]:
    true_positive = false_positive = false_negative = exact = 0
    for actual, guess in zip(expected, predicted):
        actual_set, guess_set = set(actual), set(guess)
        true_positive += len(actual_set & guess_set)
        false_positive += len(guess_set - actual_set)
        false_negative += len(actual_set - guess_set)
        exact += actual_set == guess_set
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"count": len(expected), "exact_match": exact / len(expected) if expected else 0.0, "micro_precision": precision, "micro_recall": recall, "micro_f1": f1}


def evaluate_vitaminc(client: ollama.Client, model: str, train_size: int, test_size: int) -> dict[str, Any]:
    train = read_jsonl(DATA_DIR / "vitaminc" / "train.jsonl", train_size)
    test = read_jsonl(DATA_DIR / "vitaminc" / "test.jsonl", test_size)
    context = few_shot(train, min(4, train_size))
    predictions = []
    for row in test:
        result = classify(client, model, f"""Classify the relationship between a claim and evidence as exactly one of SUPPORTS, REFUTES, or NOT ENOUGH INFO.
{context}
Claim: {row['claim']}
Evidence: {row['evidence']}
Return {{\"label\": \"SUPPORTS|REFUTES|NOT ENOUGH INFO\"}}.""")
        predictions.append(str(result.get("label", "NOT ENOUGH INFO")).upper())
    expected = [str(row["label"]).upper() for row in test]
    return {"dataset": "tals/vitaminc", "train_examples": len(train), "test_examples": len(test), "metrics": score_labels(expected, predictions), "predictions": predictions, "expected": expected}


def evaluate_opp115(client: ollama.Client, model: str, train_size: int, test_size: int) -> dict[str, Any]:
    train = read_parquet(DATA_DIR / "opp_115" / "data" / "train-00000-of-00001-58a17c1d9a42fb16.parquet", train_size)
    test = read_parquet(DATA_DIR / "opp_115" / "data" / "test-00000-of-00001-e939d436d2b73202.parquet", test_size)
    context = "\n".join(f"Example {i}: text={row['text']!r}; labels={list(row['label'])}" for i, row in enumerate(train[:4], 1))
    predictions = []
    for row in test:
        result = classify(client, model, f"""Classify this privacy-policy clause using the integer label IDs shown in the examples. Return every applicable label ID as a JSON integer array.
{context}
Clause: {row['text']}
Return {{\"labels\": [0, 1]}}.""")
        raw = result.get("labels", [])
        predictions.append(sorted({int(value) for value in raw if str(value).lstrip("-").isdigit()}))
    expected = [sorted({int(value) for value in row["label"]}) for row in test]
    return {"dataset": "alzoubi36/opp_115", "train_examples": len(train), "test_examples": len(test), "metrics": score_multilabel(expected, predictions), "predictions": predictions, "expected": expected}


def evaluate_policy_pairs(client: ollama.Client, model: str) -> dict[str, Any]:
    pairs = [
        ("Customer personal data is retained for 3 years after account closure.", "Customer personal data is retained for 1 year after account closure.", "CONTRADICTS"),
        ("Employee records are retained for 7 years after termination.", "Employee records are retained for 7 years after termination.", "SUPPORTS"),
        ("Data must be deleted within 30 days of the retention deadline.", "Data must be deleted within 7 days of the retention deadline.", "CONTRADICTS"),
        ("Legal holds override all retention schedules.", "Legal holds override all retention schedules.", "SUPPORTS"),
    ]
    expected, predicted = [], []
    for claim_a, claim_b, label in pairs:
        result = classify(client, model, f"Classify the relationship as SUPPORTS, CONTRADICTS, or UNRELATED.\nClaim A: {claim_a}\nClaim B: {claim_b}\nReturn {{\"label\": \"SUPPORTS|CONTRADICTS|UNRELATED\"}}.")
        expected.append(label)
        predicted.append(str(result.get("label", "UNRELATED")).upper())
    return {"dataset": "SuperApp policy_contradictions", "test_examples": len(pairs), "metrics": score_labels(expected, predicted), "predictions": predicted, "expected": expected}


def render_report(results: dict[str, Any], model: str) -> str:
    vitamin = results["vitaminc"]["metrics"]
    opp = results["opp_115"]["metrics"]
    policy = results["policy_pairs"]["metrics"]
    return f"""# SuperApp Evaluation Report

Generated: {results['generated_at']}

## Executive Summary

Absentia/SuperApp is an LLM-orchestration pipeline, not a trainable neural model in this repository. No weights were fitted. The training splits below were used only as few-shot calibration context; all reported metrics come from held-out examples or the known local policy-pair set.

Inference provider: Ollama  
Model: `{model}`  
Evaluation mode: deterministic sample sizes, JSON-constrained prompts, local inference

## Results

| Evaluation | Examples | Accuracy / Exact Match | F1 |
|---|---:|---:|---:|
| VitaminC claim relation | {vitamin['count']} | {vitamin['accuracy']:.3f} | {vitamin['macro_f1']:.3f} macro |
| OPP-115 privacy labels | {opp['count']} | {opp['exact_match']:.3f} exact | {opp['micro_f1']:.3f} micro |
| Known policy contradiction pairs | {policy['count']} | {policy['accuracy']:.3f} | {policy['macro_f1']:.3f} macro |

### VitaminC

Dataset: `tals/vitaminc`. Calibration examples: {results['vitaminc']['train_examples']}. Held-out examples: {results['vitaminc']['test_examples']}. This tests SUPPORTS, REFUTES, and NOT ENOUGH INFO classification over revision-based claim/evidence pairs.

### OPP-115

Dataset: `alzoubi36/opp_115`. Calibration examples: {results['opp_115']['train_examples']}. Held-out examples: {results['opp_115']['test_examples']}. This is a multi-label privacy-clause classification proxy for the company-policy coverage detector. The downloaded card exposes integer label IDs but not human-readable category names, so metrics are reported on IDs rather than renamed topics.

### SuperApp policy corpus

The four-pair smoke evaluation uses the repository's two policy versions and known expected outcomes: two contradictions and two supporting pairs. It checks the relation prompt contract used by the contradiction stage, independent of vector-store availability.

## Data Pulled

- VitaminC train and test JSONL from `tals/vitaminc`.
- OPP-115 train, validation, and test Parquet files from `alzoubi36/opp_115`.
- CUAD `README.md` and loader metadata from `theatticusproject/cuad-qa`; the full 1.6 GB dataset was not executed because its loader requires custom remote code, which was intentionally not trusted automatically.

## Limitations

- These are small evaluation samples, not publication-grade benchmark runs.
- Few-shot calibration is prompt conditioning, not model training.
- OPP-115 label IDs were evaluated without category-name mapping.
- CUAD, PubMed/RCT, codebase documentation, and engineering-spec verticals were not run in this pass.
- Results depend on the local `{model}` model, prompt wording, and Ollama runtime settings.

## Reproduction

```powershell
python scripts/run_evaluation.py --model {model} --train-size 8 --test-size 12
```

Raw JSON results: `outputs/evaluation_results.json`.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--train-size", type=int, default=8)
    parser.add_argument("--test-size", type=int, default=12)
    args = parser.parse_args()

    client = ollama.Client()
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "vitaminc": evaluate_vitaminc(client, args.model, args.train_size, args.test_size),
        "opp_115": evaluate_opp115(client, args.model, args.train_size, args.test_size),
        "policy_pairs": evaluate_policy_pairs(client, args.model),
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(results, args.model), encoding="utf-8")
    print(json.dumps({key: value.get("metrics", {}) for key, value in results.items() if isinstance(value, dict)}, indent=2))
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()