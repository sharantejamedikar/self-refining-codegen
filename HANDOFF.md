# Project handoff

## Fresh-machine setup

From the repository root, create the environment and install the project. On a
full-precision GPU cluster machine, use the cluster dependency group:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[cluster,dev]'
make data
make test
```

`make data` is the single, idempotent dataset bootstrap command. It downloads
the official HumanEval and sanitized MBPP artifacts only when absent, reproduces
the historical M7 full HumanEval compound-harness layout, atomically splits the
20 selected HumanEval development tasks, validates every canonical solution
inside `SubprocessExecutor`, writes quarantine/audit files, normalizes the valid
records, and creates the seed-42 development splits.

The completed layout is:

```text
data/
├── raw/HumanEval.jsonl.gz
├── raw/sanitized-mbpp.json
├── normalized/humaneval.jsonl             # 164 compound-harness records
├── normalized/mbpp_sanitized.jsonl         # 427 atomic-test records
├── dev/humaneval_dev.jsonl                 # 20 atomic-test records
├── dev/humaneval_dev.jsonl.meta.json
├── dev/mbpp_dev.jsonl                      # 50 records
├── dev/mbpp_dev.jsonl.meta.json
└── validation/
    ├── humaneval_dev_atomic_split_report.json
    ├── humaneval_quarantine.jsonl
    ├── humaneval_dev_quarantine.jsonl
    └── mbpp_sanitized_quarantine.jsonl
```

Successful canonical validation leaves all three quarantine files empty. Any atomic
split failure, unexpected source count, syntax error, or failing canonical test
causes the command to exit nonzero rather than silently changing the benchmark.
Re-running the command reuses raw downloads and deterministically regenerates
the derived files. To select a nonstandard data root or reproduce a different
development split explicitly, invoke:

```bash
.venv/bin/python experiments/scripts/build_datasets.py --data-dir data --seed 42
```

## HumanEval full-set taxonomy limitation

The frozen M7 full HumanEval representation stores the entire
`check(candidate)` function as one `test_cases` entry. Consequently the
executor can report only `0/1` or `1/1` at harness granularity. On failure,
the deterministic classifier sees zero passed test cases and assigns `logic`;
it cannot assign `edge_case`, because that requires separately observed passing
and failing test cases.

The compound-harness traceback recovery identifies the deepest failing
assertion so feedback can cite the relevant expression and actual/expected
values. It does **not** establish how many earlier assertions passed: reaching a
later source line suggests earlier sequential statements completed in that run,
but loops, control flow, and repeated assertion execution prevent a reliable
assertion count. Dissertation reporting must therefore describe full HumanEval
`logic`/`edge_case` labels as harness-granularity categories with `edge_case`
unobservable. Assertion-level distinction is supported for atomic
HumanEval-Dev and MBPP.
