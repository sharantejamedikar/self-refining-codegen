# Public history sanitization

Before public release, Git history was rewritten solely to remove private MSc
dissertation drafting material and operational AI-agent workflow files. Commit
authors, author/committer dates, source history, configurations, tests, notebooks,
documentation evidence, and experiment-result contents were not modified for the
purpose of changing authorship or scientific provenance.

The purged path groups were:

- `AGENTS.md` and nested `AGENTS.md` files;
- `CLAUDE.md`;
- `HANDOFF.md`;
- `PROMPTS.md`;
- the complete `dissertation/` directory.

The release tree before and immediately after filtering had the identical Git tree
object `7a13feb2639d2fedd54b3ed07348865b958a56b4`. The `configs/`, `src/`, `tests/`,
`experiments/results/`, `docs/validation/`, and `notebooks/` subtree object IDs
were also identical across that boundary. All 86 historical result directories
remain present.

History rewriting necessarily changed descendant commit IDs. Frozen run artefacts
retain their original, pre-sanitization `git_commit.txt` values to avoid altering
experimental records. [`history-rewrite-commit-map.txt`](history-rewrite-commit-map.txt)
maps every rewritten pre-sanitization commit to its public equivalent. A
40-zero new value means the original commit became empty after the selected paths
were removed and has no separate public commit.

The private pre-rewrite history is not required to run the software, inspect the
frozen evidence, or recompute the documented analysis. Public commit-map entries
support auditability of identifiers embedded in immutable experiment records; they
do not restore the purged file contents.
