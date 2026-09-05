# SuperApp Evaluation Report

Generated: 2026-09-05T17:44:21.540092+00:00

## Executive Summary

Absentia/SuperApp is an LLM-orchestration pipeline, not a trainable neural model in this repository. No weights were fitted. The training splits below were used only as few-shot calibration context; all reported metrics come from held-out examples or the known local policy-pair set.

Inference provider: Ollama  
Model: `llama3.2`  
Evaluation mode: deterministic sample sizes, JSON-constrained prompts, local inference

## Results

| Evaluation | Examples | Accuracy / Exact Match | F1 |
|---|---:|---:|---:|
| VitaminC claim relation | 12 | 0.167 | 0.162 macro |
| OPP-115 privacy labels | 12 | 0.000 exact | 0.100 micro |
| Known policy contradiction pairs | 4 | 1.000 | 1.000 macro |

### VitaminC

Dataset: `tals/vitaminc`. Calibration examples: 8. Held-out examples: 12. This tests SUPPORTS, REFUTES, and NOT ENOUGH INFO classification over revision-based claim/evidence pairs.

### OPP-115

Dataset: `alzoubi36/opp_115`. Calibration examples: 8. Held-out examples: 12. This is a multi-label privacy-clause classification proxy for the company-policy coverage detector. The downloaded card exposes integer label IDs but not human-readable category names, so metrics are reported on IDs rather than renamed topics.

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
- Results depend on the local `llama3.2` model, prompt wording, and Ollama runtime settings.

## Reproduction

```powershell
python scripts/run_evaluation.py --model llama3.2 --train-size 8 --test-size 12
```

Raw JSON results: `outputs/evaluation_results.json`.
