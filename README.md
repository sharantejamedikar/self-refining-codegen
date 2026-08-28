# Self-Refining Code Generation Using Execution Feedback

This repository contains the research software artefact for an MSc Artificial
Intelligence project at the University of Surrey. It evaluates whether execution
feedback can improve generated Python programs, compared with allocating the same
maximum generation opportunity to independent sampling.

## Overview

The refinement pipeline performs:

```text
code generation -> resource-limited subprocess execution
                -> deterministic failure classification
                -> hybrid execution feedback -> revision
                -> convergence decision
```

The system does not train or fine-tune a model. It compares inference-time
policies for using up to five generation opportunities.

## Research question

The central allocation question is whether additional inference should repair a
failed candidate using execution feedback or independently sample alternatives.
The study also tests whether adaptive convergence avoids unnecessary continuation
without reducing the set of tasks ever solved.

## Models

- `Qwen/Qwen2.5-Coder-7B-Instruct`
- `codellama/CodeLlama-13b-Instruct-hf`

These are materially different experimental configurations: architecture,
parameter scale, and numerical representation are confounded. Their comparison
does not isolate a causal model-family or quantisation effect.

## Benchmarks

- HumanEval: 164 tasks
- sanitized MBPP: 427 tasks
- HumanEval Pro: 164 tasks
- MBPP Pro: 378 tasks

Correctness means passing the available function-level Python tests; it is not a
claim of production or repository-scale correctness.

## Inference policies

- **Single-pass:** one candidate at temperature 0.2.
- **Best-of-5:** five independent candidates at temperature 0.8; a task is solved
  if any candidate passes all tests.
- **Adaptive refinement:** at most five generations, stopping according to the
  convergence rules below.
- **Fixed-k=5 refinement:** five generations are attempted for convergence
  analysis, including an artificial contradictory post-success request after a
  successful execution.

Best-of-5 is finite-set any-success discovery, not project `pass@5` and not a
deployable selector: it uses test outcomes unavailable at deployment. It is
matched on a common maximum five-generation opportunity, not on tokens, latency,
or realised calls.

## Feedback

The implementation supports template, trace, and hybrid feedback. Hybrid routing
uses template feedback for success, syntax errors, timeouts, and ordinary runtime
errors; it uses trace feedback for logic failures, edge cases, and
recursion-related runtime errors.

## Adaptive convergence

Decisions use this priority:

1. success;
2. maximum iterations (five generations);
3. stagnation (patience two: unchanged pass rate and identical error-message
   hash);
4. oscillation (an exact code-hash recurrence within the recent three
   iterations).

## Headline results

| Model | Benchmark | Single-pass | Best-of-5 | Adaptive |
|---|---:|---:|---:|---:|
| Qwen | HumanEval | 142/164 (86.59%) | 152/164 (92.68%) | 148/164 (90.24%) |
| Qwen | sanitized MBPP | 307/427 (71.90%) | 337/427 (78.92%) | 352/427 (82.44%) |
| CodeLlama | HumanEval | 68/164 (41.46%) | 102/164 (62.20%) | 87/164 (53.05%) |
| CodeLlama | sanitized MBPP | 192/427 (44.96%) | 263/427 (61.59%) | 257/427 (60.19%) |

| Model | Pro benchmark | Single-pass | Best-of-5 | Adaptive |
|---|---:|---:|---:|---:|
| Qwen | HumanEval Pro | 107/164 | 129/164 | 115/164 |
| Qwen | MBPP Pro | 228/378 | 289/378 | 257/378 |
| CodeLlama | HumanEval Pro | 47/164 | 71/164 | 55/164 |
| CodeLlama | MBPP Pro | 143/378 | 206/378 | 175/378 |

Adaptive refinement exceeded single-pass in all eight authoritative core
conditions. Its ranking against Best-of-5 was conditional: all four Pro
conditions favoured Best-of-5, while Qwen on sanitized MBPP favoured adaptive
refinement (352 versus 337 solved; exact conditional two-sided McNemar
`p = 0.048873892`, condition-specific and unadjusted for multiplicity).

Adaptive and fixed-k refinement had identical ever-solved task sets in all eight
standard and Pro convergence conditions. Forced continuation found no additional
authoritative task and added 480--1,488 calls. Adaptive refinement used
58.5--75.7% fewer calls than Best-of-5 across the eight core conditions. Any
observed post-success regression must be interpreted with the contradictory
prompt caveat above, not as evidence that natural continued refinement is
inherently unstable.

Detailed frozen tables and run mappings are in
[`docs/dissertation_results_tables.md`](docs/dissertation_results_tables.md).

## Repository structure

```text
configs/             experiment, model, dataset, and device YAML
docs/                reporting tables, validation records, reproducibility guide
experiments/scripts/ config-driven dataset, evaluation, and analysis entry points
experiments/results/ frozen per-run and per-problem evidence
notebooks/           analysis/progress notebook
src/                 generation, execution, feedback, convergence, loop, analysis
tests/               non-GPU unit and integration tests
```

## Installation and quick validation

Python 3.10 or newer is required. For a lightweight development installation:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
make test
make lint
```

The smallest end-to-end check uses the mock generator and requires prepared
development data:

```bash
.venv/bin/python experiments/scripts/run_mock_single_pass.py --limit 1
```

See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for dataset preparation,
analysis of frozen results, and optional heavyweight evaluation commands. A new
user does not need to rerun the GPU campaign to validate the software artefact.

## Safety

Generated programs are evaluated in resource-limited subprocesses with
Python-level restrictions. This is **not** an adversarially hardened secure
sandbox and must not be treated as safe isolation for hostile untrusted code.

## Reproducibility caveats and limitations

- Model and dataset identities are pinned where available, but software versions
  were not recorded uniformly across every historical run.
- Accelerator, numerical precision, and backend differences can prevent
  bitwise-identical generations.
- The two model configurations are confounded, and the benchmarks cover only
  test-bounded function-level Python correctness.
- Training-data overlap or benchmark contamination cannot be excluded.
- The complete-policy Best-of-5 comparison is not a decoding-controlled causal
  ablation of feedback alone.
- Fixed seeds cover a limited sample of decoding randomness.
- The intended feedback-length manipulation did not produce distinct realised
  feedback lengths, so it does not support a length-effect claim.
- The executor is not production-grade security isolation.

## Dissertation

This repository accompanies the MSc Artificial Intelligence dissertation
“Self-Refining Code Generation Using Execution Feedback” at the University of
Surrey (2026).

## Citation

```text
Sharan Teja Medikar. Self-Refining Code Generation Using Execution Feedback.
MSc Artificial Intelligence dissertation software artefact, University of
Surrey, 2026.
```

## Licence

No explicit open-source licence has been granted for this repository. Copyright
and reuse rights therefore remain with the author unless separately stated.
