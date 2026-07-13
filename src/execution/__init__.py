"""Sandboxed execution interfaces and backends."""

from execution.base import (
    ExecutionResult,
    ExecutionTrace,
    Executor,
    TestResult,
    TraceEvent,
)
from execution.subprocess_executor import SubprocessExecutor

__all__ = [
    "ExecutionResult",
    "ExecutionTrace",
    "Executor",
    "SubprocessExecutor",
    "TestResult",
    "TraceEvent",
]
