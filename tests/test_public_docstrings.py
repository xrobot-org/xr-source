"""验证运行时源码持续具备中文说明和代码段落注释。
Regression tests for Chinese runtime documentation and code comments.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

_CJK = re.compile(r"[\u3400-\u9fff]")


def _runtime_python_files() -> list[Path]:
    """返回全部 runtime Python 源文件。
    Return all runtime Python source files.
    """
    package_root = Path(__file__).parents[1] / "src" / "xr_syntax"
    return sorted(package_root.rglob("*.py"))


def _definitions_without_chinese_docstrings() -> list[str]:
    """收集缺少中文 docstring 的模块、类、函数和方法。
    Collect runtime modules, classes, functions, and methods missing Chinese docstrings.
    """
    package_root = Path(__file__).parents[1] / "src" / "xr_syntax"
    missing: list[str] = []

    for path in _runtime_python_files():
        module = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(package_root)

        if not _CJK.search(ast.get_docstring(module) or ""):
            missing.append(f"{relative}:<module>")

        for node in ast.walk(module):
            if not isinstance(
                node,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue
            if not _CJK.search(ast.get_docstring(node) or ""):
                missing.append(f"{relative}:{node.name}")

    return missing


def _files_without_chinese_line_comments() -> list[str]:
    """收集没有任何中文 # comment token 的 runtime 文件。
    Collect runtime files that contain no Chinese line-comment token.
    """
    package_root = Path(__file__).parents[1] / "src" / "xr_syntax"
    missing: list[str] = []

    for path in _runtime_python_files():
        source = path.read_text(encoding="utf-8")
        comments = (
            token.string
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type == tokenize.COMMENT
        )
        if not any(_CJK.search(comment) for comment in comments):
            missing.append(str(path.relative_to(package_root)))

    return missing


def test_every_runtime_definition_has_chinese_docstring() -> None:
    """要求每个 runtime 模块、类和函数都带中文说明。
    Require Chinese documentation on every runtime module, class, and function.
    """
    assert _definitions_without_chinese_docstrings() == []


def test_every_runtime_file_has_chinese_line_comment() -> None:
    """要求每个 runtime 文件至少有一条真正的中文 # 注释。
    Require at least one real Chinese line comment in every runtime file.
    """
    assert _files_without_chinese_line_comments() == []
