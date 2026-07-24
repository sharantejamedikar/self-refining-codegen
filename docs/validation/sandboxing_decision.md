# Sandboxing implementation and scoping decision

**Decision date:** 2026-07-25  
**Decision:** retain the resource-limited subprocess executor for this research
project; do not add Docker as a requirement for the experimental pipeline.

## Decision summary

The project deliberately used subprocess-based sandboxing throughout its
development and M7 experiments. Docker was originally identified as a possible
M6 hardening step if the environment allowed it, but it was explicitly never a
blocker. After evaluating the actual threat model, implemented controls, and
operational evidence, Docker hardening was scoped out of the dissertation
pipeline.

This is a reasoned methodological choice, not an abandoned implementation
task. The existing `Executor` interface still keeps the execution backend
swappable, but implementing a Docker backend would not materially advance the
research question within the remaining project timeline.

## Threat model

The executed programs are solutions generated locally by the project's
quantized Qwen code model for fixed HumanEval and sanitized MBPP tasks. The
system accepts no code from untrusted external users, has no multi-user
service, and is not deployed as a network-facing application. Its purpose is a
controlled, single-researcher experiment on a local machine, not a production
code-execution service.

Generated code is nevertheless treated as untrusted because it may contain
accidental infinite loops, excessive allocation, subprocess creation, file
operations, or network calls. The principal risks in scope are therefore
accidental resource exhaustion and unintended local side effects from
model-generated benchmark solutions. Deliberately adversarial code submitted
by hostile users, tenant-to-tenant isolation, and protection of production
infrastructure are outside this project's threat model.

## Controls actually implemented

All generated code is executed through `SubprocessExecutor`; it is never
passed to `exec` or `eval` in the main experiment process. The executor applies
the following controls:

- **Process isolation:** every test runs in a fresh Python subprocess, launched
  in isolated mode with `python -I`.
- **Temporary-directory isolation:** every test receives a fresh temporary
  working directory containing only its generated program. The directory is
  removed after execution.
- **Execution timeout:** a wall-clock deadline is enforced for the complete
  problem, including its individual tests. A timed-out process is terminated
  and recorded as a timeout result.
- **Memory and CPU limits:** where supported by the host, the child process
  receives `RLIMIT_AS` and `RLIMIT_CPU` limits. The experiment configuration
  supplies the memory ceiling, while the CPU ceiling is derived from the
  configured timeout.
- **No network access:** the generated program is prefixed with guards that
  deny high- and low-level socket creation and common subprocess or shell
  escape paths. On macOS, when `sandbox-exec` is available and passes a probe,
  the child additionally runs under an operating-system profile that denies
  network access.
- **Restricted environment:** the child receives a minimal environment rather
  than inheriting the experiment process's complete environment.

These controls are proportionate to accidental or incidental misbehaviour by
locally generated benchmark code. They should not be interpreted as a
Docker-equivalent containment boundary against a determined adversary.

## Operational evidence

The eight authoritative full-scale M7 runs executed **7,340 generated
candidate programs**:

| Configuration | HumanEval candidates | MBPP candidates |
|---|---:|---:|
| Single pass | 164 | 427 |
| Best of five | 820 | 2,135 |
| Adaptive refinement | 202 | 637 |
| Fixed five-iteration refinement | 820 | 2,135 |
| **Total** | **2,006** | **5,334** |

The same subprocess backend was also used throughout the preceding development
runs and automated integration tests. Across the eight full-scale M7 runs and
all development runs, the project recorded **zero security incidents** while
executing thousands of generated samples. Timeouts and generated-code
exceptions occurred as expected and were contained and recorded as experiment
outcomes.

This history is evidence that the controls were sufficient for the observed
workload and stated threat model. It is not evidence that the subprocess
backend is secure against arbitrary malicious code, nor does the absence of an
incident prove that no stronger isolation could ever be needed.

## Trade-off and applicability

Docker would provide a stronger OS-level isolation boundary and more explicit
control over filesystem visibility, process capabilities, and networking. It
would be warranted if this system accepted code from untrusted external users,
served multiple users, ran as a network-facing service, or were deployed in
production. Under those conditions, container hardening—and potentially
additional isolation beyond ordinary Docker—would be a prerequisite rather
than an optional enhancement.

For this dissertation, Docker would also introduce environment-specific setup,
portability, and reproducibility work unrelated to the central comparison of
single-pass generation, compute-matched sampling, and execution-feedback
refinement. Given the controlled local threat model, the safeguards already in
place, the incident-free execution history, and the dissertation timeline,
retaining the subprocess executor is the deliberate scope boundary.

## Methodological reporting

The methodology chapter should describe the executor as a
**resource-limited subprocess sandbox appropriate to a controlled local
research setting**. It should report the implemented controls and the
limitations above, and should not claim container-grade or adversarial
isolation. Docker should be presented as a stronger requirement for a
different deployment threat model, not as missing work needed to validate the
current experiments.
