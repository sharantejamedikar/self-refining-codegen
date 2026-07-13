"""Tests for subprocess execution isolation and structured outcomes."""

from __future__ import annotations

import pytest

from execution import SubprocessExecutor
from execution import subprocess_executor as executor_module


def test_executor_reports_pass_fail_and_streams() -> None:
    executor = SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None)
    result = executor.execute(
        "def add(a, b):\n    print('called')\n    return a + b",
        ["assert add(1, 2) == 3", "assert add(2, 2) == 5"],
    )
    assert not result.passed
    assert result.passed_tests == 1
    assert result.total_tests == 2
    assert result.tests[0].stdout == "called\n"
    assert result.tests[1].exception_type == "AssertionError"
    assert "Traceback" in (result.tests[1].traceback or "")
    assert result.to_dict()["total_tests"] == 2


def test_executor_timeout_and_network_denial() -> None:
    executor = SubprocessExecutor(timeout_seconds=0.1, memory_limit_mb=None)
    timeout = executor.execute("while True: pass", ["assert True"]).tests[0]
    network = executor.execute("import socket\nsocket.socket()", ["assert True"]).tests[
        0
    ]
    assert timeout.timed_out and timeout.exception_type == "TimeoutError"
    assert network.exception_type == "PermissionError"
    assert "disabled" in (network.exception_message or "")


def test_executor_syntax_empty_tests_and_constructor_validation() -> None:
    executor = SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None)
    syntax = executor.execute("def broken(:", ["assert True"])
    assert syntax.tests[0].exception_type == "SyntaxError"
    assert not executor.execute("x = 1", []).passed
    with pytest.raises(ValueError, match="timeout"):
        SubprocessExecutor(timeout_seconds=0)
    with pytest.raises(ValueError, match="memory"):
        SubprocessExecutor(memory_limit_mb=0)


def test_executor_builds_resource_limit_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, tuple[int, int]]] = []

    class FakeResource:
        RLIMIT_AS = 1
        RLIMIT_CPU = 2

        @staticmethod
        def setrlimit(kind: int, limits: tuple[int, int]) -> None:
            calls.append((kind, limits))

    monkeypatch.setattr(executor_module, "resource", FakeResource)
    callback = SubprocessExecutor(
        timeout_seconds=1.5, memory_limit_mb=256
    )._limit_resources()
    assert callback is not None
    callback()
    assert calls == [
        (FakeResource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024)),
        (FakeResource.RLIMIT_CPU, (2, 2)),
    ]


def test_executor_ignores_unsupported_resource_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnsupportedResource:
        RLIMIT_AS = 1
        RLIMIT_CPU = 2

        @staticmethod
        def setrlimit(kind: int, limits: tuple[int, int]) -> None:
            del kind, limits
            raise OSError("unsupported")

    monkeypatch.setattr(executor_module, "resource", UnsupportedResource)
    callback = SubprocessExecutor(memory_limit_mb=128)._limit_resources()
    assert callback is not None
    callback()
