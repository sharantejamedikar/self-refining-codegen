"""Resource-limited subprocess backend for untrusted generated Python code."""

from __future__ import annotations

import ast
import json
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

from execution.base import (
    ExecutionResult,
    ExecutionTrace,
    Executor,
    TestResult,
    TraceEvent,
)

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

_ASSERTION_MARKER = "__SRCG_ASSERTION_VALUES__"
_TRACE_MARKER = "__SRCG_TRACE__"


class SubprocessExecutor(Executor):
    """Run every test in a fresh temporary directory and Python process."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        memory_limit_mb: int | None = 512,
        python_executable: str = sys.executable,
        collect_trace: bool = False,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if memory_limit_mb is not None and memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive or None")
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.python_executable = python_executable
        self.collect_trace = collect_trace

    def execute(self, code: str, test_cases: list[str]) -> ExecutionResult:
        """Execute isolated tests under one shared per-problem wall-clock budget."""

        started = time.monotonic()
        deadline = started + self.timeout_seconds
        outcomes: list[TestResult] = []
        for index, test_case in enumerate(test_cases):
            if time.monotonic() >= deadline:
                outcomes.extend(
                    self._budget_exhausted(case) for case in test_cases[index:]
                )
                break
            outcome = self._run_test(code, test_case, deadline)
            outcomes.append(outcome)
            if outcome.timed_out:
                outcomes.extend(
                    self._budget_exhausted(case) for case in test_cases[index + 1 :]
                )
                break
        return ExecutionResult(
            passed=bool(outcomes) and all(outcome.passed for outcome in outcomes),
            tests=tuple(outcomes),
            duration_seconds=time.monotonic() - started,
        )

    def _run_test(self, code: str, test_case: str, deadline: float) -> TestResult:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="srcg-") as directory:
            temp_dir = Path(directory)
            program = temp_dir / "program.py"
            instrumented_test, assertion_expression = self._instrument_assertion(
                test_case
            )
            program.write_text(
                self._build_program(code, instrumented_test), encoding="utf-8"
            )
            command = self._sandbox_command(program)
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                return self._budget_exhausted(
                    test_case, duration_seconds=time.monotonic() - started
                )
            try:
                completed = subprocess.run(
                    command,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=remaining_seconds,
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
                        f"Exceeded {self.timeout_seconds:g}s per-problem "
                        "wall-clock limit"
                    ),
                    traceback=None,
                    stdout=self._decode_timeout_stream(error.stdout),
                    stderr=self._decode_timeout_stream(error.stderr),
                    duration_seconds=duration,
                    timed_out=True,
                )

        trace, stderr = self._parse_trace(completed.stderr)
        exception_type, exception_message = self._parse_exception(stderr)
        actual_value, expected_value = self._parse_assertion_values(exception_message)
        if actual_value is not None:
            exception_message = (
                f"assertion comparison failed: actual={actual_value}; "
                f"expected={expected_value}"
            )
        return TestResult(
            test_case=test_case,
            passed=completed.returncode == 0,
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=stderr if completed.returncode else None,
            stdout=completed.stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
            assertion_expression=assertion_expression,
            actual_value=actual_value,
            expected_value=expected_value,
            trace=trace,
        )

    def _build_program(self, code: str, test_case: str) -> str:
        candidate = code.rstrip()
        prefix = f"{_NETWORK_GUARD}\n"
        if not self.collect_trace:
            return f"{prefix}{candidate}\n\n{test_case.rstrip()}\n"

        candidate_start = prefix.count("\n") + 1
        candidate_lines = candidate.splitlines()
        candidate_end = candidate_start + len(candidate_lines) - 1
        sources = {
            candidate_start + offset: line.strip()
            for offset, line in enumerate(candidate_lines)
        }
        indented_test = "\n".join(
            f"    {line}" if line else "    "
            for line in test_case.rstrip().splitlines()
        )
        tracer = f"""\
import json as __srcg_json_7f31
import sys as __srcg_sys_7f31
__srcg_trace_start_7f31 = {candidate_start}
__srcg_trace_end_7f31 = {candidate_end}
__srcg_trace_sources_7f31 = {sources!r}
__srcg_trace_events_7f31 = []
__srcg_trace_max_depth_7f31 = 0
__srcg_trace_deepest_7f31 = None
def __srcg_trace_7f31(frame, event, arg):
    global __srcg_trace_max_depth_7f31, __srcg_trace_deepest_7f31
    line_number = frame.f_lineno
    is_candidate = (
        frame.f_code.co_filename == __file__
        and __srcg_trace_start_7f31 <= line_number <= __srcg_trace_end_7f31
    )
    if is_candidate:
        depth = 0
        cursor = frame
        while cursor is not None:
            if (
                cursor.f_code.co_filename == __file__
                and __srcg_trace_start_7f31
                <= cursor.f_lineno
                <= __srcg_trace_end_7f31
            ):
                depth += 1
            cursor = cursor.f_back
        if depth > __srcg_trace_max_depth_7f31:
            __srcg_trace_max_depth_7f31 = depth
            __srcg_trace_deepest_7f31 = frame.f_code.co_name
        if event == "line":
            item = {{
                "line_number": line_number - __srcg_trace_start_7f31 + 1,
                "function": frame.f_code.co_name,
                "source": __srcg_trace_sources_7f31.get(line_number, ""),
            }}
            if not __srcg_trace_events_7f31 or item != __srcg_trace_events_7f31[-1]:
                __srcg_trace_events_7f31.append(item)
                del __srcg_trace_events_7f31[:-12]
    return __srcg_trace_7f31
__srcg_sys_7f31.settrace(__srcg_trace_7f31)
try:
{indented_test}
finally:
    __srcg_sys_7f31.settrace(None)
    __srcg_payload_7f31 = {{
        "recent_events": __srcg_trace_events_7f31,
        "max_call_depth": __srcg_trace_max_depth_7f31,
        "deepest_function": __srcg_trace_deepest_7f31,
    }}
    print(
        "{_TRACE_MARKER}" + __srcg_json_7f31.dumps(__srcg_payload_7f31),
        file=__srcg_sys_7f31.stderr,
    )
"""
        return f"{prefix}{candidate}\n\n{tracer}"

    @staticmethod
    def _parse_trace(stderr: str) -> tuple[ExecutionTrace | None, str]:
        payload: dict[str, object] | None = None
        retained: list[str] = []
        for line in stderr.splitlines(keepends=True):
            stripped = line.rstrip("\r\n")
            if stripped.startswith(_TRACE_MARKER):
                try:
                    decoded = json.loads(stripped[len(_TRACE_MARKER) :])
                except json.JSONDecodeError:
                    retained.append(line)
                else:
                    if isinstance(decoded, dict):
                        payload = decoded
                continue
            retained.append(line)
        if payload is None:
            return None, "".join(retained)
        raw_events = payload.get("recent_events", [])
        if not isinstance(raw_events, list):
            return None, "".join(retained)
        try:
            events = tuple(
                TraceEvent(
                    line_number=int(item["line_number"]),
                    function=str(item["function"]),
                    source=str(item["source"]),
                )
                for item in raw_events
                if isinstance(item, dict)
            )
            trace = ExecutionTrace(
                recent_events=events,
                max_call_depth=int(payload.get("max_call_depth", 0)),
                deepest_function=(
                    str(payload["deepest_function"])
                    if payload.get("deepest_function") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError):
            return None, "".join(retained)
        return trace, "".join(retained)

    def _budget_exhausted(
        self, test_case: str, duration_seconds: float = 0.0
    ) -> TestResult:
        return TestResult(
            test_case=test_case,
            passed=False,
            exception_type="TimeoutError",
            exception_message=(
                f"Exceeded {self.timeout_seconds:g}s per-problem wall-clock limit"
            ),
            traceback=None,
            stdout="",
            stderr="",
            duration_seconds=duration_seconds,
            timed_out=True,
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

    @staticmethod
    def _instrument_assertion(test_case: str) -> tuple[str, str | None]:
        """Capture operands for a simple comparison without evaluating either twice."""

        try:
            module = ast.parse(test_case)
        except SyntaxError:
            return test_case, None
        assertions = [node for node in ast.walk(module) if isinstance(node, ast.Assert)]
        if len(assertions) != 1:
            return test_case, None
        assertion = assertions[0]
        expression = ast.unparse(assertion.test)
        comparison = assertion.test
        if not isinstance(comparison, ast.Compare) or len(comparison.ops) != 1:
            return test_case, expression
        if len(comparison.comparators) != 1:
            return test_case, expression

        actual_name = "__srcg_assertion_actual_7f31"
        expected_name = "__srcg_assertion_expected_7f31"
        assignment_actual = ast.Assign(
            targets=[ast.Name(actual_name, ast.Store())], value=comparison.left
        )
        assignment_expected = ast.Assign(
            targets=[ast.Name(expected_name, ast.Store())],
            value=comparison.comparators[0],
        )
        message = ast.BinOp(
            left=ast.Constant(_ASSERTION_MARKER),
            op=ast.Add(),
            right=ast.Call(
                func=ast.Name("repr", ast.Load()),
                args=[
                    ast.Tuple(
                        elts=[
                            ast.Call(
                                func=ast.Name("repr", ast.Load()),
                                args=[ast.Name(actual_name, ast.Load())],
                                keywords=[],
                            ),
                            ast.Call(
                                func=ast.Name("repr", ast.Load()),
                                args=[ast.Name(expected_name, ast.Load())],
                                keywords=[],
                            ),
                        ],
                        ctx=ast.Load(),
                    )
                ],
                keywords=[],
            ),
        )
        replacement = ast.Assert(
            test=ast.Compare(
                left=ast.Name(actual_name, ast.Load()),
                ops=comparison.ops,
                comparators=[ast.Name(expected_name, ast.Load())],
            ),
            msg=message,
        )
        for node in [module, *ast.walk(module)]:
            if (
                isinstance(node, ast.Module | ast.FunctionDef)
                and assertion in node.body
            ):
                index = node.body.index(assertion)
                node.body[index : index + 1] = [
                    assignment_actual,
                    assignment_expected,
                    replacement,
                ]
                return ast.unparse(ast.fix_missing_locations(module)), expression
        return test_case, expression

    @staticmethod
    def _parse_assertion_values(
        exception_message: str | None,
    ) -> tuple[str | None, str | None]:
        if not exception_message or not exception_message.startswith(_ASSERTION_MARKER):
            return None, None
        payload = exception_message[len(_ASSERTION_MARKER) :]
        try:
            values = ast.literal_eval(payload)
        except (SyntaxError, ValueError):
            return None, None
        if not (
            isinstance(values, tuple)
            and len(values) == 2
            and all(isinstance(value, str) for value in values)
        ):
            return None, None
        return values
