"""Regression test that keeps the public runtime API documented."""

from __future__ import annotations

import ast
from pathlib import Path


def _public_api_without_docstrings() -> list[str]:
    package_root = Path(__file__).parents[1] / "src" / "xr_source"
    missing: list[str] = []

    for path in sorted(package_root.rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"))

        for node in module.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue

            if ast.get_docstring(node) is None:
                missing.append(f"{path.relative_to(package_root)}:{node.name}")

            if not isinstance(node, ast.ClassDef):
                continue

            for member in node.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if member.name.startswith("_"):
                    continue
                if ast.get_docstring(member) is None:
                    missing.append(
                        f"{path.relative_to(package_root)}:{node.name}.{member.name}"
                    )

    return missing


def test_public_runtime_api_has_docstrings() -> None:
    """Require at least one contract sentence on every public runtime API member."""
    assert _public_api_without_docstrings() == []
