"""检查仓库中的中英文双语文档与代码说明。

The audit is static and never imports target modules, so optional dependencies are not
triggered while checking documentation coverage.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

_CHINESE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_ENGLISH_WORD = re.compile(r"\b[A-Za-z][A-Za-z0-9+-]*\b")
_ENGLISH_SENTENCE = re.compile(r"[A-Za-z][^.!?\n]{4,}[.!?](?:\s|$)")
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
class DocumentationIssue:
    """记录一处缺少中文、英文或双语对应内容的说明问题。

    Record one documentation issue where Chinese, English, or a bilingual counterpart is
    missing.
    """

    path: Path
    line: int
    kind: str
    name: str
    missing: str


def _has_chinese(text: str | None) -> bool:
    """判断说明文本中是否至少包含一个中文字符。

    Return whether documentation text contains at least one Chinese character.
    """

    return bool(text and _CHINESE.search(text))


def _has_english(text: str | None) -> bool:
    """判断说明文本中是否存在完整英文说明，而不把孤立技术标识符当成英文文档。

    Return whether text contains an English prose sentence rather than only isolated
    technical identifiers.
    """

    if not text:
        return False
    normalized = " ".join(text.split())
    if len(_ENGLISH_WORD.findall(normalized)) < 4:
        return False
    return bool(_ENGLISH_SENTENCE.search(normalized))


def _python_files(root: Path) -> list[Path]:
    """返回仓库内需要审计的 Python 文件，并排除构建与缓存目录。

    Return Python files that must be audited while excluding build and cache directories.
    """

    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in _SKIP_PARTS for part in path.parts)
    )


def _qualified_name(stack: list[str], name: str) -> str:
    """把类/函数嵌套栈与当前名称拼成可读限定名。

    Join the class/function nesting stack and current name into a readable qualified name.
    """

    return ".".join([*stack, name]) if stack else name


class _Visitor(ast.NodeVisitor):
    """收集模块、类、函数和异步函数的双语 docstring 缺口。

    Collect bilingual docstring violations for modules, classes, functions, and async
    functions.
    """

    def __init__(self, path: Path) -> None:
        """保存当前文件路径，并初始化限定名栈和问题列表。

        Store the current path and initialize the qualified-name stack and issue list.
        """

        self.path = path
        self.stack: list[str] = []
        self.issues: list[DocumentationIssue] = []

    def _check(self, node: ast.AST, kind: str, name: str) -> None:
        """检查一个 AST 节点的 docstring 是否同时包含中文和英文说明。

        Check whether one AST node has a docstring containing both Chinese and English
        documentation.
        """

        doc = ast.get_docstring(node, clean=False)
        qualified = _qualified_name(self.stack, name)
        if not _has_chinese(doc):
            self.issues.append(
                DocumentationIssue(
                    self.path, getattr(node, "lineno", 1), kind, qualified, "Chinese"
                )
            )
        if not _has_english(doc):
            self.issues.append(
                DocumentationIssue(
                    self.path, getattr(node, "lineno", 1), kind, qualified, "English"
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """检查类说明，并在遍历方法时维护类限定名。

        Check class documentation and maintain the class-name stack while visiting methods.
        """

        self._check(node, "class", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """检查同步函数/方法说明，并继续审计内部嵌套函数。

        Check synchronous function or method documentation and continue into nested
        functions.
        """

        self._check(node, "function", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """检查异步函数/方法说明，并继续审计内部嵌套函数。

        Check asynchronous function or method documentation and continue into nested
        functions.
        """

        self._check(node, "async-function", node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def _audit_python_docstrings(root: Path) -> list[DocumentationIssue]:
    """审计全部 Python 模块、类和函数的中英文 docstring。

    Audit bilingual docstrings for every Python module, class, and function.
    """

    issues: list[DocumentationIssue] = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        module_doc = ast.get_docstring(tree, clean=False)
        if not _has_chinese(module_doc):
            issues.append(DocumentationIssue(path, 1, "module", path.name, "Chinese"))
        if not _has_english(module_doc):
            issues.append(DocumentationIssue(path, 1, "module", path.name, "English"))
        visitor = _Visitor(path)
        visitor.visit(tree)
        issues.extend(visitor.issues)
    return issues


def _audit_markdown(root: Path) -> list[DocumentationIssue]:
    """审计 README 与 docs 下 Markdown 是否同时提供完整中文和 English 区段。

    Audit README and docs Markdown files for complete Chinese and English sections.
    """

    paths = [root / "README.md", *sorted((root / "docs").glob("*.md"))]
    issues: list[DocumentationIssue] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "## 中文" not in text or not _has_chinese(text):
            issues.append(DocumentationIssue(path, 1, "markdown", path.name, "Chinese section"))
        if "## English" not in text or not _has_english(text):
            issues.append(DocumentationIssue(path, 1, "markdown", path.name, "English section"))
    return issues


def _audit_inline_comments(root: Path) -> list[DocumentationIssue]:
    """检查中文行内注释块是否存在紧邻的英文对应说明。

    Check that every Chinese inline-comment block has an adjacent English counterpart.
    """

    issues: list[DocumentationIssue] = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        comments = [
            token
            for token in tokens
            if token.type == tokenize.COMMENT and _has_chinese(token.string)
        ]
        index = 0
        while index < len(comments):
            token = comments[index]
            line_no, column = token.start
            prefix = lines[line_no - 1][:column]
            if prefix.strip():
                if "/ EN:" not in token.string:
                    issues.append(
                        DocumentationIssue(
                            path,
                            line_no,
                            "comment",
                            token.string,
                            "English inline counterpart",
                        )
                    )
                index += 1
                continue

            # 连续同缩进中文注释视作一个块，只要求块后紧邻至少一行 # EN:。
            # EN: Consecutive Chinese comments with the same indentation form one block; the
            #     block must be followed immediately by at least one # EN: line.
            indent = prefix
            end_line = line_no
            index += 1
            while index < len(comments):
                next_token = comments[index]
                next_line, next_col = next_token.start
                next_prefix = lines[next_line - 1][:next_col]
                if next_line != end_line + 1 or next_prefix != indent or next_prefix.strip():
                    break
                end_line = next_line
                index += 1

            following = lines[end_line] if end_line < len(lines) else ""
            if not following.startswith(f"{indent}# EN:"):
                issues.append(
                    DocumentationIssue(
                        path,
                        line_no,
                        "comment-block",
                        token.string,
                        "English comment block",
                    )
                )
    return issues


def audit(root: Path) -> list[DocumentationIssue]:
    """执行完整双语审计，并返回所有 docstring、Markdown 和行内注释问题。

    Run the complete bilingual audit and return all docstring, Markdown, and inline-comment
    issues.
    """

    return [
        *_audit_python_docstrings(root),
        *_audit_markdown(root),
        *_audit_inline_comments(root),
    ]


def main() -> None:
    """执行命令行审计，并在存在双语缺口时返回非零退出码。

    Run the command-line audit and return a non-zero exit status when bilingual
    documentation is incomplete.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="只打印问题，不以失败状态退出 / report issues without failing",
    )
    args = parser.parse_args()

    issues = audit(args.root)
    for item in issues:
        print(
            f"{item.path}:{item.line}: {item.kind} {item.name} "
            f"(missing {item.missing})"
        )
    print(f"missing_bilingual_docs={len(issues)}")

    if issues and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
