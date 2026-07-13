"""Strict AST-based extraction of atomic HumanEval assertions."""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HarnessSplitFailure:
    """One HumanEval harness that could not be split safely."""

    task_id: str
    reason: str


@dataclass(frozen=True)
class AtomicSplitReport:
    """Auditable summary of HumanEval harness splitting."""

    total_harnesses: int
    atomically_split: int
    failed: int
    total_assertions: int
    failures: tuple[HarnessSplitFailure, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report."""

        data = asdict(self)
        data["failures"] = [asdict(failure) for failure in self.failures]
        return data


def write_atomic_split_report(report: AtomicSplitReport, path: str | Path) -> Path:
    """Write an atomic-split validation report as deterministic JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


class UnsafeHumanEvalHarnessError(ValueError):
    """Raised when atomic extraction cannot preserve harness semantics safely."""


class HumanEvalAtomicSplitError(ValueError):
    """Raised when one or more dataset harnesses fail strict atomic extraction."""

    def __init__(self, report: AtomicSplitReport) -> None:
        self.report = report
        super().__init__(
            "HumanEval atomic split failed: "
            f"{report.atomically_split}/{report.total_harnesses} split, "
            f"{report.failed}/{report.total_harnesses} failed"
        )


_DYNAMIC_MODULES = {"random", "secrets", "time", "uuid"}


def split_humaneval_harness(test_source: str, entry_point: str) -> tuple[str, ...]:
    """Split a safe ``check(candidate)`` into independent assertion harnesses.

    The transformation preserves all module-level imports, constants, and helpers,
    but refuses constructs whose state or dynamically generated data could make
    isolated assertion execution differ from the original harness.
    """

    if not entry_point.isidentifier():
        raise UnsafeHumanEvalHarnessError(f"invalid entry point {entry_point!r}")
    try:
        module = ast.parse(test_source)
    except SyntaxError as error:
        raise UnsafeHumanEvalHarnessError(
            f"test harness syntax error: {error}"
        ) from error

    checks = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "check"
    ]
    if len(checks) != 1:
        raise UnsafeHumanEvalHarnessError(
            f"expected exactly one check() function, found {len(checks)}"
        )
    check = checks[0]
    _validate_check_signature(check)
    if not check.body:
        raise UnsafeHumanEvalHarnessError("check() contains no assertions")
    if not all(isinstance(statement, ast.Assert) for statement in check.body):
        kinds = sorted(
            {
                type(statement).__name__
                for statement in check.body
                if not isinstance(statement, ast.Assert)
            }
        )
        raise UnsafeHumanEvalHarnessError(
            f"check() contains non-assert statements: {kinds}"
        )

    module_bindings = _module_bindings(module, check)
    for assertion in check.body:
        _validate_assertion(assertion, module_bindings)

    tests = tuple(
        _build_single_assertion_module(module, check, assertion, entry_point, index)
        for index, assertion in enumerate(check.body, start=1)
    )
    return tests


def _validate_check_signature(check: ast.FunctionDef) -> None:
    arguments = check.args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
        len(positional) != 1
        or positional[0].arg != "candidate"
        or arguments.vararg is not None
        or arguments.kwarg is not None
        or arguments.kwonlyargs
        or arguments.defaults
    ):
        raise UnsafeHumanEvalHarnessError(
            "check() must accept exactly one required positional argument "
            "named candidate"
        )
    if check.decorator_list:
        raise UnsafeHumanEvalHarnessError("decorated check() functions are unsupported")


def _module_bindings(module: ast.Module, check: ast.FunctionDef) -> dict[str, ast.stmt]:
    bindings: dict[str, ast.stmt] = {}
    for statement in module.body:
        if statement is check or _is_check_call(statement):
            continue
        if isinstance(statement, ast.FunctionDef | ast.ClassDef):
            bindings[statement.name] = statement
        elif isinstance(statement, ast.Import | ast.ImportFrom):
            for alias in statement.names:
                name = alias.asname or alias.name.split(".")[0]
                bindings[name] = statement
        elif isinstance(statement, ast.Assign | ast.AnnAssign):
            for name in _assigned_names(statement):
                bindings[name] = statement
        elif not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            raise UnsafeHumanEvalHarnessError(
                f"unsupported module-level statement: {type(statement).__name__}"
            )
    return bindings


def _validate_assertion(
    assertion: ast.Assert, module_bindings: dict[str, ast.stmt]
) -> None:
    if any(
        isinstance(node, ast.NamedExpr | ast.Yield | ast.YieldFrom | ast.Await)
        for node in ast.walk(assertion)
    ):
        raise UnsafeHumanEvalHarnessError(
            "assertion contains assignment, yield, or await expression"
        )
    stored = [
        node.id
        for node in ast.walk(assertion)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del)
    ]
    if stored:
        raise UnsafeHumanEvalHarnessError(
            f"assertion dynamically binds names: {sorted(set(stored))}"
        )

    loaded_names = {
        node.id
        for node in ast.walk(assertion)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    for name in loaded_names - {"candidate"}:
        binding = module_bindings.get(name)
        if isinstance(binding, ast.Assign | ast.AnnAssign) and not _is_immutable(
            binding
        ):
            raise UnsafeHumanEvalHarnessError(
                f"assertion depends on shared mutable module state {name!r}"
            )
        if isinstance(binding, ast.FunctionDef):
            _validate_helper(name, binding, module_bindings)
        if (
            isinstance(binding, ast.Import | ast.ImportFrom)
            and name in _DYNAMIC_MODULES
        ):
            raise UnsafeHumanEvalHarnessError(
                f"assertion depends on dynamic data source {name!r}"
            )

    for call in (node for node in ast.walk(assertion) if isinstance(node, ast.Call)):
        root = _call_root(call.func)
        if root in _DYNAMIC_MODULES:
            raise UnsafeHumanEvalHarnessError(
                f"assertion calls dynamic data source {root!r}"
            )


def _validate_helper(
    name: str, helper: ast.FunctionDef, module_bindings: dict[str, ast.stmt]
) -> None:
    if any(isinstance(node, ast.Global | ast.Nonlocal) for node in ast.walk(helper)):
        raise UnsafeHumanEvalHarnessError(f"helper {name!r} accesses non-local state")
    helper_loads = {
        node.id
        for node in ast.walk(helper)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    for loaded in helper_loads:
        binding = module_bindings.get(loaded)
        if isinstance(binding, ast.Assign | ast.AnnAssign) and not _is_immutable(
            binding
        ):
            raise UnsafeHumanEvalHarnessError(
                f"helper {name!r} depends on shared mutable state {loaded!r}"
            )
    for call in (node for node in ast.walk(helper) if isinstance(node, ast.Call)):
        root = _call_root(call.func)
        if root in _DYNAMIC_MODULES:
            raise UnsafeHumanEvalHarnessError(
                f"helper {name!r} calls dynamic data source {root!r}"
            )


def _build_single_assertion_module(
    module: ast.Module,
    check: ast.FunctionDef,
    assertion: ast.Assert,
    entry_point: str,
    index: int,
) -> str:
    single_check = copy.deepcopy(check)
    single_check.body = [copy.deepcopy(assertion)]
    body: list[ast.stmt] = []
    for statement in module.body:
        if statement is check:
            body.append(single_check)
        elif not _is_check_call(statement):
            body.append(copy.deepcopy(statement))
    body.append(
        ast.Expr(
            value=ast.Call(
                func=ast.Name(id="check", ctx=ast.Load()),
                args=[ast.Name(id=entry_point, ctx=ast.Load())],
                keywords=[],
            )
        )
    )
    atomic_module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    return f"# HumanEval atomic assertion {index}\n{ast.unparse(atomic_module)}"


def _is_check_call(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "check"
    )


def _assigned_names(statement: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = (
        statement.targets if isinstance(statement, ast.Assign) else [statement.target]
    )
    return {
        node.id
        for target in targets
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }


def _is_immutable(statement: ast.Assign | ast.AnnAssign) -> bool:
    value = statement.value
    if value is None:
        return False
    try:
        literal = ast.literal_eval(value)
    except (ValueError, TypeError):
        return False
    return _is_immutable_literal(literal)


def _is_immutable_literal(value: object) -> bool:
    if isinstance(value, str | bytes | int | float | complex | bool | type(None)):
        return True
    if isinstance(value, tuple):
        return all(_is_immutable_literal(item) for item in value)
    return False


def _call_root(function: ast.expr) -> str | None:
    while isinstance(function, ast.Attribute):
        function = function.value
    return function.id if isinstance(function, ast.Name) else None
