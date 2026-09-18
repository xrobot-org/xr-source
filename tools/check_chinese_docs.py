"""检查仓库中的中文文件说明和函数说明。

该脚本只做静态 AST 审计，不导入被检查模块，因此不会触发可选依赖。
正式 CI 会运行它，防止后续新增 Python 文件或函数时漏掉中文说明。
"""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path

_CHINESE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
}


@dataclass(frozen=True, slots=True)
class MissingDoc:
    """记录一处缺失或不含中文的说明。"""

    path: Path
    line: int
    kind: str
    name: str


def _has_chinese(text: str | None) -> bool:
    """判断说明文本中是否至少包含一个中文字符。"""
    return bool(text and _CHINESE.search(text))


def _python_files(root: Path) -> list[Path]:
    """返回仓库内需要审计的 Python 文件，排除构建和缓存目录。"""
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in _SKIP_PARTS for part in path.parts)
    )


def _qualified_name(stack: list[str], name: str) -> str:
    """把类/函数嵌套栈和当前名称拼成可读的限定名。"""
    return ".".join([*stack, name]) if stack else name


class _Visitor(ast.NodeVisitor):
    """收集类、函数和异步函数的中文说明缺口。"""

    def __init__(self, path: Path) -> None:
        """保存当前文件路径并初始化限定名栈与缺口列表。"""
        self.path = path
        self.stack: list[str] = []
        self.missing: list[MissingDoc] = []

    def _check(self, node: ast.AST, kind: str, name: str) -> None:
        """检查一个 AST 节点的 docstring 是否存在且包含中文。"""
        doc = ast.get_docstring(node, clean=False)
        if not _has_chinese(doc):
            self.missing.append(
                MissingDoc(
                    self.path,
                    getattr(node, "lineno", 1),
                    kind,
                    _qualified_name(self.stack, name),
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """检查类说明，并在遍历方法时维护类限定名。"""
        self._check(node, "class", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """检查同步函数/方法说明，并继续审计其内部嵌套函数。"""
        self._check(node, "function", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """检查异步函数/方法说明，并继续审计其内部嵌套函数。"""
        self._check(node, "async-function", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def audit(root: Path) -> list[MissingDoc]:
    """审计全部 Python 文件并返回所有中文说明缺口。"""
    missing: list[MissingDoc] = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if not _has_chinese(ast.get_docstring(tree, clean=False)):
            missing.append(MissingDoc(path, 1, "module", path.name))
        visitor = _Visitor(path)
        visitor.visit(tree)
        missing.extend(visitor.missing)
    return missing


def main() -> None:
    """执行命令行审计并按需要返回非零退出码。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="只打印问题，不以失败状态退出。",
    )
    args = parser.parse_args()

    missing = audit(args.root)
    for item in missing:
        print(f"{item.path}:{item.line}: {item.kind} {item.name}")
    print(f"missing_chinese_docs={len(missing)}")

    if missing and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
