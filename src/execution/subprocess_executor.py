"""Resource-limited subprocess backend for untrusted generated Python code."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from execution.base import ExecutionResult, Executor, TestResult

try:
    import resource
except ImportError:  # pragma: no cover - Windows is not an experiment target.
    resource = None  # type: ignore[assignment]


_NETWORK_GUARD = """\
import socket as _sandbox_socket
import _socket as _sandbox_low_level_socket
import os as _sandbox_os
import subprocess as _sandbox_subprocess
def _network_denied(*args, **kwargs):
    raise PermissionError("Network access is disabled in the execution sandbox")
_sandbox_socket.socket = _network_denied
_sandbox_socket.create_connection = _network_denied
_sandbox_low_level_socket.socket = _network_denied
_sandbox_subprocess.Popen = _network_denied
_sandbox_subprocess.run = _network_denied
_sandbox_subprocess.call = _network_denied
_sandbox_subprocess.check_call = _network_denied
_sandbox_subprocess.check_output = _network_denied
_sandbox_os.system = _network_denied
if hasattr(_sandbox_os, "fork"):
    _sandbox_os.fork = _network_denied
"""


class SubprocessExecutor(Executor):
    """Run every test in a fresh temporary directory and Python process."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        memory_limit_mb: int | None = 512,
        python_executable: str = sys.executable,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if memory_limit_mb is not None and memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive or None")
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.python_executable = python_executable

    def execute(self, code: str, test_cases: list[str]) -> ExecutionResult:
        """Execute candidate plus each test in separate sandboxed subprocesses."""

        started = time.monotonic()
        outcomes = tuple(self._run_test(code, test_case) for test_case in test_cases)
        return ExecutionResult(
            passed=bool(outcomes) and all(outcome.passed for outcome in outcomes),
            tests=outcomes,
            duration_seconds=time.monotonic() - started,
        )

    def _run_test(self, code: str, test_case: str) -> TestResult:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="srcg-") as directory:
            temp_dir = Path(directory)
            program = temp_dir / "program.py"
            program.write_text(
                f"{_NETWORK_GUARD}\n{code.rstrip()}\n\n{test_case.rstrip()}\n",
                encoding="utf-8",
            )
            command = self._sandbox_command(program)
            try:
                completed = subprocess.run(
                    command,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env=self._minimal_environment(),
                    preexec_fn=self._limit_resources(),
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                duration = time.monotonic() - started
                return TestResult(
                    test_case=test_case,
                    passed=False,
                    exception_type="TimeoutError",
                    exception_message=(
                        f"Exceeded {self.timeout_seconds:g}s wall-clock limit"
                    ),
                    traceback=None,
                    stdout=self._decode_timeout_stream(error.stdout),
                    stderr=self._decode_timeout_stream(error.stderr),
                    duration_seconds=duration,
                    timed_out=True,
                )

        exception_type, exception_message = self._parse_exception(completed.stderr)
        return TestResult(
            test_case=test_case,
            passed=completed.returncode == 0,
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=completed.stderr if completed.returncode else None,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=time.monotonic() - started,
        )

    def _sandbox_command(self, program: Path) -> list[str]:
        sandbox_exec = (
            shutil.which("sandbox-exec") if sys.platform == "darwin" else None
        )
        base = [self.python_executable, "-I", str(program)]
        if sandbox_exec is None or not self._can_apply_macos_sandbox(sandbox_exec):
            return base
        profile = "(version 1) (allow default) (deny network*)"
        return [sandbox_exec, "-p", profile, *base]

    @staticmethod
    def _can_apply_macos_sandbox(sandbox_exec: str) -> bool:
        probe = subprocess.run(
            [
                sandbox_exec,
                "-p",
                "(version 1) (allow default) (deny network*)",
                "/usr/bin/true",
            ],
            capture_output=True,
            check=False,
        )
        return probe.returncode == 0

    def _limit_resources(self) -> Callable[[], None] | None:
        if resource is None or self.memory_limit_mb is None:
            return None
        limit = self.memory_limit_mb * 1024 * 1024

        def apply_limits() -> None:
            # RLIMIT_AS is unavailable or unsafe in some macOS/container hosts.
            with suppress(OSError, ValueError):
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            cpu_seconds = max(1, int(self.timeout_seconds) + 1)
            with suppress(OSError, ValueError):
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

        return apply_limits

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        allowed = ("PATH", "SYSTEMROOT", "TMPDIR")
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        environment.update({"PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1"})
        return environment

    @staticmethod
    def _parse_exception(stderr: str) -> tuple[str | None, str | None]:
        if not stderr:
            return None, None
        last_line = stderr.rstrip().splitlines()[-1]
        match = re.match(
            r"(?P<type>[A-Za-z_][\w.]*(?:Error|Exception))(?:: (?P<msg>.*))?", last_line
        )
        if match:
            return match.group("type"), match.group("msg") or ""
        return "ProcessError", last_line

    @staticmethod
    def _decode_timeout_stream(stream: bytes | str | None) -> str:
        if stream is None:
            return ""
        return stream.decode(errors="replace") if isinstance(stream, bytes) else stream
