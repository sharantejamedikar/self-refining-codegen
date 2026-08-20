# Tier 3 cluster-operation methodology note

## GPU 1 preflight threshold

From commit `44c06f0` onward, the sustained-idleness utilization threshold for
GPU 1 was raised from 5% to 25%, while the memory threshold remained 500 MiB.
This change was approved by the professor before the Tier 3 campaign. GPU 1
hosts the display stack and therefore showed persistent low-level utilization
that could exceed 5% even when no compute workload was present; the earlier
threshold produced false refusals. The revised guard still required every
sample in the sustained preflight window to remain strictly below both the
25% utilization and 500 MiB memory limits.

## Parallel use

Both cluster GPUs were used in parallel for portions of Tier 3. Each job was
assigned explicitly to a GPU, and GPU 1 access remained conditional on the
approved sustained-idleness preflight. Parallel scheduling changed campaign
throughput, not the per-configuration model, dataset, seed, generation, or
execution protocol recorded in each run artifact.

## Supervision and integrity auditing

The Tier 3 campaign ran largely unattended and autonomously over an extended
period, with periodic integrity audits rather than continuous manual
supervision. Audits checked process and GPU state, run completion, expected
problem counts, stored configuration snapshots and seeds, per-problem JSON,
summary consistency, and repository status. This operating model is recorded
for methodological transparency; all reported measurements remain derived
from the committed immutable artifacts.
