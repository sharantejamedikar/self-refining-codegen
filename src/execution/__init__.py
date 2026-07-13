"""Sandboxed execution interfaces and backends."""

from execution.base import ExecutionResult, Executor, TestResult
from execution.subprocess_executor import SubprocessExecutor

__all__ = ["ExecutionResult", "Executor", "SubprocessExecutor", "TestResult"]
