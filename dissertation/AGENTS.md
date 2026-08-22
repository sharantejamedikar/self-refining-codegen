# Dissertation Instructions

## Scope

This directory contains the MSc dissertation:

"Self-Refining Code Generation Using Execution Feedback"

The experimental project is COMPLETE and FROZEN.

Do not run new model-generation experiments unless explicitly authorised by the user.

## Authoritative project state

- Dissertation reporting configurations: 44
- Core reporting runs: 32
- Sensitivity/ablation runs: 12
- Development/validation runs: 25
- Invalid/superseded runs: 17
- Total committed result directories: 86
- Experiment values missing: NONE
- Qwen MBPP Pro adaptive model calls: 620
- Final experiment/documentation closeout commit:
  db4fa23e0f460aec2500f487b23f8d29ad9a9c6a
- Final pytest state: 154 passed

## Frozen evidence

Treat these locations as READ ONLY unless explicitly authorised:

- ../experiments/results/
- ../src/
- ../tests/
- ../configs/
- ../docs/validation/
- ../notebooks/progress_m1_to_cluster.ipynb

Do not modify, delete, rerun, regenerate, or reinterpret experimental artifacts merely to make the dissertation easier to write.

## Project evidence hierarchy

For numerical and implementation claims, prefer:

1. committed experiment artifacts
2. ../docs/dissertation_results_tables.md
3. ../docs/validation/
4. ../notebooks/progress_m1_to_cluster.ipynb
5. frozen configs and per-problem JSON

Never invent missing values.

Never use superseded or invalid runs as authoritative evidence.

## Dissertation requirements

- Preserve the official University of Surrey LaTeX template unless a change is necessary.
- British English.
- Formal academic register.
- IEEE referencing.
- Critical analysis over description.
- Distinguish observation from interpretation.
- Distinguish statistical significance from practical significance.
- Explicitly discuss limitations and alternative explanations.
- Do not overstate causal or generalisation claims.
- Never fabricate citations.
- Every external technical claim must have a verifiable source.
- Every project-specific numerical claim must be traceable to frozen project evidence.

## Important terminology

Use consistently:

- Qwen2.5-Coder-7B-Instruct
- CodeLlama-13B-Instruct
- HumanEval: 164 tasks
- sanitized MBPP: 427 tasks
- HumanEval Pro: 164 tasks
- MBPP Pro: 378 tasks

Methods:

- Single-pass
- Best-of-5
- Adaptive refinement
- Fixed-k=5 refinement

Convergence:

- success
- maximum iterations
- stagnation
- oscillation

Do not conflate:

- fixed-k ever-solved
- fixed-k final-iteration

Do not present Qwen versus CodeLlama as a pure model-family comparison because precision/model configuration are confounded.

## AI assistance disclosure

OpenAI Codex may be used to assist with code/LaTeX generation and mechanical editing during dissertation development.

Research problem formulation, system architecture, experimental design, benchmark/model selection, refinement methodology, evaluation protocol, interpretation of results and dissertation argumentation remain the author's responsibility.

## Codex editing rules

When asked to edit the dissertation:

1. Read this file first.
2. Read the relevant frozen project evidence before inserting project facts.
3. Show intended files before editing when changes are substantial.
4. Modify only dissertation/ unless explicitly authorised otherwise.
5. Compile after structural LaTeX changes.
6. Do not silently change numerical results.
7. Stop and report any inconsistency between sources.
8. Do not add unverified bibliography entries.
