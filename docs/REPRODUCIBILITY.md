# Reproducibility guide

This guide separates lightweight software validation from optional benchmark and
model evaluation. The committed experiment artefacts are frozen; reproducing the
analysis does not require rerunning model inference.

## Environment

The package requires Python 3.10 or newer. Direct dependencies and development
tools are pinned in `pyproject.toml`, `requirements.txt`, and
`requirements-dev.txt`. The optional `cluster` dependency group pins the
Hugging Face/PyTorch stack used by the supported full-precision backend. This is
version pinning rather than a complete platform lock: operating-system, driver,
CUDA, and accelerator details were not recorded uniformly for every historical
run.

Create a lightweight environment for tests and frozen-result analysis:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

For the Hugging Face GPU backend, install the optional cluster group on a
compatible accelerator host:

```bash
.venv/bin/python -m pip install -e '.[cluster,dev]'
```

The 13B configuration and a full-precision 7B model must not be loaded on the
project's 24 GiB Apple Silicon development machine. Local development used an
Ollama-hosted 4-bit Qwen model; all authoritative reported values came from the
committed cluster runs.

## Non-GPU validation

Run the full test and quality suite without downloading a model:

```bash
make test
make lint
```

Equivalent direct commands are:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m black --check src tests experiments/scripts
```

Tests use `MockGenerator` and do not require model weights or a GPU.

## Benchmark preparation and validation

Benchmark data are deliberately not committed. The build command downloads the
upstream HumanEval, sanitized MBPP, HumanEval Pro, and MBPP Pro artefacts; checks
the expected source counts; validates canonical solutions through
`SubprocessExecutor`; writes quarantine/audit records; normalizes the datasets;
and creates deterministic seed-42 development splits.

```bash
make data
```

or explicitly:

```bash
.venv/bin/python experiments/scripts/build_datasets.py \
  --data-dir data --seed 42
```

Expected validated counts are 164 HumanEval, 427 sanitized MBPP, 164 HumanEval
Pro, and 378 MBPP Pro tasks. Development subsets contain 20 HumanEval and 50 MBPP
tasks; the HumanEval feedback-strategy subset contains 100 tasks. The command
fails rather than silently dropping records if canonical validation or an
expected-count check fails. Dataset preparation uses network access and executes
canonical benchmark solutions in the resource-limited subprocess executor.

## Configuration

YAML files in `configs/` record dataset paths, model identities and revisions,
generation settings, executor limits, seeds, feedback policy, and convergence
settings. Device profiles are selected with `--profile mac`, `cluster`, or
`colab`. Inspect a configuration before running it: files whose names contain
`full` target full benchmark sets and are retained for provenance, not routine
development.

The authoritative policies use at most five generation opportunities.
Single-pass and refinement use temperature 0.2; Best-of-5 uses temperature 0.8.
Adaptive convergence uses the priority success, maximum iterations, stagnation,
then oscillation.

## Analysis from frozen results

The 86 directories in `experiments/results/` preserve historical authoritative,
development/validation, invalid, incomplete, duplicate, and superseded evidence.
Their contents must not be edited or treated interchangeably. The authoritative
boundary and exact immutable run mapping are documented in:

- `docs/dissertation_results_tables.md`;
- `docs/validation/full_precision_tier1_summary.md`;
- `docs/validation/standard_benchmark_statistics.json`;
- `docs/validation/tier3_pro_statistics.json`;
- the per-run configuration snapshots, summaries, and problem JSON.

Recreate the committed standard and Pro statistical reports from the mapped
frozen runs with:

```bash
.venv/bin/python experiments/scripts/analyze_statistics.py \
  --config configs/standard_benchmark_statistics.yaml
.venv/bin/python experiments/scripts/analyze_statistics.py \
  --config configs/tier3_pro_statistics.yaml
```

These commands recompute reporting files, so use a clean checkout or direct their
output as appropriate when verifying byte-for-byte repository state. The public
release does not recompute frozen statistics.

## Optional model evaluation

Model evaluation is heavyweight and is not required for installation
verification. After preparing data and installing a compatible backend, the
entry points are:

```bash
.venv/bin/python experiments/scripts/run_single_pass.py \
  --config CONFIG.yaml --profile cluster
.venv/bin/python experiments/scripts/run_best_of_k.py \
  --config CONFIG.yaml --profile cluster
.venv/bin/python experiments/scripts/run_refinement.py \
  --config CONFIG.yaml --profile cluster
```

Use a development-set configuration during debugging. Full-set configuration
files document the frozen campaign and should only be used for a deliberate
replication. Runs write a configuration snapshot, Git commit, seeds, per-problem
JSON, and summary data beneath `experiments/results/` unless an explicit run
directory is supplied.

Generation need not be bitwise reproducible across accelerator types, backend
versions, numerical representations, or software stacks even when model revision,
configuration, and seed are fixed.

## Executor boundary

Generated programs execute only through the `Executor` interface. The subprocess
backend uses a temporary directory, wall-clock timeout, and platform-dependent
resource limits and Python-level restrictions. It is suitable for controlled
benchmark code, not adversarial hostile programs; it is not container-grade or a
production security boundary.

## Frozen evidence boundary

The public evidence records completed experiments. Authoritative numbers are the
44 reporting configurations: 32 core and 12 sensitivity/ablation configurations.
Development, validation, invalid, incomplete, duplicate, and superseded runs are
retained for auditability but must not be promoted to authoritative evidence.
Correctness remains bounded by the committed function-level tests, and the model
comparison does not isolate architecture, scale, precision, or quantisation.

The public-release history was sanitized to remove private dissertation drafting
and operational workflow files. Consequently, commit identifiers recorded inside
frozen artefacts refer to the pre-sanitization lineage. See
[`HISTORY_REWRITE.md`](HISTORY_REWRITE.md) and the accompanying commit map when
tracing those identifiers; result contents were not changed.
