# Prompts for Claude Code / Codex

## Setup (one-time)

1. Create an empty repo folder, drop `AGENTS.md` in the root.
   - Claude Code reads `AGENTS.md` automatically.
   - For Codex, duplicate it as `AGENTS.md` (same content) — Codex reads that file.
2. Start the agent inside the repo folder.

---

## KICKOFF PROMPT (first session — paste exactly)

```
Read AGENTS.md in full before doing anything. Confirm you've read it by listing
the three guardrails you consider most binding on your behavior, in one line each.

Then execute Milestone M1 only:

1. Scaffold the repository exactly per section 4 of AGENTS.md, with pyproject.toml,
   pinned requirements, .gitignore (exclude data/, results/, models), and a Makefile
   or justfile with targets: test, lint, format.
2. Implement the typed config system (YAML → dataclass) with device auto-detection
   (CUDA → MPS → CPU) and a config override for mac/cluster/colab profiles.
3. Implement the dataset module: download + load HumanEval and MBPP (sanitized),
   normalize both into the unified JSON schema from the planning doc (task_id,
   prompt, canonical_solution, test_cases, difficulty, tags), and run validation —
   every canonical solution must pass its own tests inside the sandbox executor,
   with failures quarantined and logged, never silently fixed.
4. Create stratified dev splits: HumanEval-Dev (20) and MBPP-Dev (50), seeded,
   written to data/ with the seed recorded.
5. Implement SubprocessExecutor per the Executor interface: temp dir, wall-clock
   timeout (10s), memory limit where the OS allows, no network, structured result
   (per-test pass/fail, exception type/message/traceback, stdout, stderr,
   duration). Generated code must never run in the main process.
6. Implement MockGenerator (canned correct + canned buggy outputs) and the
   single-pass runner that ties loader → generator → executor → per-problem JSON
   result.
7. Write pytest tests for every module including an integration test running
   3 problems end-to-end with MockGenerator. Run the full suite and show me the
   real output.

Definition of done: `make test` is green, and one command runs a HumanEval problem
through generate → execute → pass/fail with the mock backend.

Work incrementally: after each numbered step, give me a one-line status before
moving on. Do not start M2. Do not download any model weights this session.
Finish with the end-of-session summary required by AGENTS.md section 7.
```

---

## PER-SESSION PROMPT TEMPLATE (every later session)

```
Read AGENTS.md first.

Current state: [what exists, last milestone completed, anything broken]
Last results: [paste latest dev-set numbers or "none yet"]

Today's task: Milestone [Mx] — [one specific goal].

Before writing code: tell me in ≤5 bullets your plan and anything in my request
you think is a mistake. Then proceed.

Run the test suite before you finish and paste the real output. End with the
AGENTS.md section-7 summary.
```

---

## RESULTS-REVIEW PROMPT (after every experiment run)

```
Read AGENTS.md. Here are results from [experiment name]: [paste summary CSV / JSON].

Act as a skeptical dissertation examiner. Answer:
1. What would you challenge about these numbers or the methodology behind them?
2. Are any comparisons unfair or confounded (compute, temperature, prompt length)?
3. Which follow-up experiment or check would most strengthen or falsify the claim?
4. Write the 3-sentence honest summary of this result as it should appear in the
   dissertation — no overselling.
```

---

## Session discipline (for you, not the agent)

- One milestone per session. If a session sprawls, stop and restart with a fresh
  context — long agent sessions drift.
- Commit after every green test suite. Never let the agent batch a day of work
  into one commit.
- If the agent reports a number, find the JSON file it came from. If you can't,
  the number doesn't exist.
- Update "Current state" in the per-session template yourself; don't let the
  agent summarize its own previous session from memory.
```
