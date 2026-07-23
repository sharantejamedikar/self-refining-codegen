# HTCondor cluster setup and validation

This is a preparation runbook. No remote cluster run has been performed. The
first jobs must use the development split; do not touch a full benchmark until
the environment and one-problem smoke test are recorded and reviewed.

## 1. Confirm site-specific details

Ask the cluster administrator for the login host, shared-filesystem policy,
GPU requirement expression, permitted CUDA/PyTorch versions, outbound access
policy, maximum wall time, memory units, and whether jobs may write directly
to the repository. Replace the `<SITE_...>` values below with their answer.
Do not guess these values.

The intended job pattern is one independent experiment configuration per
HTCondor job, one GPU per job, with logs and result artifacts isolated by job.
Do not split one problem across GPUs and do not run two model processes on one
GPU. Submit Qwen and CodeLlama as separate jobs; later matrix configurations
remain separate jobs so failures and seeds are auditable.

## 2. Create the environment

From a cluster login node in a checked-out repository:

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[cluster,dev]'
.venv/bin/python -c "import torch, transformers; print(torch.__version__, transformers.__version__, torch.cuda.is_available())"
```

The last value must be `True` inside an allocated GPU job. Login nodes may
correctly report `False`; never load either model on a login node. If Hugging
Face access requires a pre-populated cache, download both pinned revisions
using the administrator-approved mechanism before disabling outbound access.

Record `git rev-parse HEAD`, `nvidia-smi`, Python/package versions, and the two
config snapshots with every validation run.

## 3. One-problem smoke test

Create `cluster_smoke.sub` outside version control (or adapt the administrator's
approved template):

```text
universe = vanilla
initialdir = <ABSOLUTE_REPOSITORY_PATH>
executable = <ABSOLUTE_REPOSITORY_PATH>/.venv/bin/python
arguments = experiments/scripts/run_single_pass.py --config $(config) --profile cluster --limit 1

request_gpus = 1
request_cpus = <SITE_CPUS>
request_memory = <SITE_MEMORY>
request_disk = <SITE_DISK>
+MaxRuntime = <SITE_MAX_RUNTIME_SECONDS>

environment = "HF_HOME=<SITE_HF_CACHE>;TOKENIZERS_PARALLELISM=false"
output = cluster_logs/$(ClusterId).$(ProcId).out
error = cluster_logs/$(ClusterId).$(ProcId).err
log = cluster_logs/$(ClusterId).log

queue config from (
configs/cluster_qwen_hf_zero_shot_humaneval_dev.yaml
)
```

Create `cluster_logs/`, then submit and inspect:

```bash
mkdir -p cluster_logs
condor_submit cluster_smoke.sub
condor_q
condor_tail -f <CLUSTER_ID>.0
condor_history <CLUSTER_ID> -long
```

If the site does not use a shared filesystem, add its approved
`should_transfer_files`, `transfer_input_files`, and `transfer_output_files`
settings. Do not invent transfer rules because dataset and model-cache sizes
make accidental per-job transfers expensive.

## 4. Acceptance checks before matrix submission

- The job log shows a CUDA allocation and the resolved config records
  `device.accelerator: cuda`.
- The pinned HF revision is present in the run's config snapshot.
- The model metadata says `backend: huggingface`, has no quantization setting,
  and records CUDA plus the selected dtype.
- Exactly one development problem produces a per-problem JSON, summary CSV,
  and run summary without model download or CUDA out-of-memory errors.
- Generated code runs only through `SubprocessExecutor`; no cluster wrapper
  executes candidate code directly.
- Re-run the smoke test for CodeLlama by changing the single queued config to
  `configs/cluster_codellama_hf_zero_shot_humaneval_dev.yaml`.

Only after both smoke tests pass should the Tier 1/Tier 2 experiment configs
be frozen and submitted. Use one queue item per config, retain fixed seeds,
and never overwrite or reuse a run directory.

## 5. Failure triage

- `torch.cuda.is_available() == False`: inspect the matched execute node,
  GPU request expression, CUDA module/container, and installed PyTorch build.
- Revision/download failure: verify the exact 40-character revision and the
  approved HF cache or outbound-network policy.
- CUDA out of memory: capture `nvidia-smi` and job memory/GPU type; do not
  silently quantize, lower model size, or alter reported-run precision.
- Eviction or wall-time termination: preserve logs and incremental result
  JSON, then request the correct site runtime class before resubmission.
- Held job: use `condor_q <CLUSTER_ID> -better-analyze` and send its output to
  the administrator.
