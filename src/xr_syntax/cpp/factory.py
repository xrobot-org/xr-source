"""提供常见 C++ 源码片段的 parser-backed 工厂，包括 include、声明、表达式和保护区。
Factories that create parser-backed C++ syntax fragments from structured inputs.
"""

from __future__ import annotations

from collections.abc import Iterable

from xr_syntax.core import (
    GreenChild,
    GreenElement,
    GreenNode,
    GreenToken,
    GreenTrivia,
    SyntaxNode,
)
from xr_syntax.format import Group, Indent, concat, join, line, render, softline

from .document import CppDocument
from .parser import CppParser


class CppFactory:
    """创建常用 C++ parser-backed 片段，并通过重新解析保证结构与文本一致。
    Create validated C++ syntax fragments by parsing generated source snippets.
    """
    def __init__(self, parser: CppParser | None = None, *, width: int = 100) -> None:
        """初始化 C++ 片段工厂并保存布局宽度。
        Initialize the C++ fragment factory and store its layout width.
        """
        self.parser = parser or CppParser()
        self.width = width

    def include(self, header: str, *, system: bool = False) -> GreenElement:
        """创建一条本地或 system include 指令并返回其 green 语法。
        Create one parser-backed include directive.
        """
        delimiters = ("<", ">") if system else ('"', '"')
        source = f"#include {delimiters[0]}{header}{delimiters[1]}\n"
        return self._first(source, "preproc_include").green

    def comment(self, text: str, *, block: bool = False) -> GreenElement:
        """创建一条 C++ 行注释或块注释片段。
        Create one parser-backed line or block comment.
        """
        source = f"/* {text} */" if block else f"// {text}"
        return self._first(source, "comment").green

    def directive(self, source: str) -> GreenElement:
        """创建一条预处理指令，并按需要补齐行尾换行。
        Create and validate one preprocessor directive fragment.
        """
        document = CppDocument.parse(source.rstrip() + "\n", parser=self.parser)
        for child in document.root.syntax_children:
            return child.green
        raise ValueError("directive did not produce syntax")

    def raw(self, source: str) -> GreenElement:
        """创建不解释内部结构的原始源码 trivia。
        Create opaque generated text when no more specific factory is useful.
        """
        return GreenToken("raw", source, named=True)

    def user_region(
        self,
        name: str,
        body: Iterable[GreenElement] = (),
    ) -> GreenElement:
        """创建带 User Code Begin/End 标记的保护区域。
        Create a paired User Code region containing parser-backed fragments.
        """
        return self._region(
            "xr_user_region",
            f"/* User Code Begin {name} */",
            f"/* User Code End {name} */",
            body,
        )

    def format_region(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建 clang-format off/on 保护区域。
        Create a paired clang-format off/on region.
        """
        return self._region(
            "xr_format_region",
            "// clang-format off",
            "// clang-format on",
            body,
        )

    def lint_region(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建 NOLINTBEGIN/NOLINTEND 保护区域。
        Create a paired NOLINTBEGIN/NOLINTEND region.
        """
        return self._region(
            "xr_lint_region",
            "// NOLINTBEGIN",
            "// NOLINTEND",
            body,
        )

    def expression(self, text: str) -> GreenElement:
        """把表达式片段包入临时上下文解析，并返回结构化 expression green 元素。
        Parse and return one expression syntax subtree.
        """
        document = CppDocument.parse(
            f"auto __xr_expr() -> decltype(auto) {{ return {text}; }}",
            parser=self.parser,
        )
        statement = document.nodes("return_statement")[0]
        for child in statement.named_children:
            return child.green
        raise ValueError("expression did not produce syntax")

    def statement(self, text: str) -> GreenElement:
        """把语句片段放入临时函数体解析，并返回结构化 statement green 元素。
        Parse and return one statement syntax subtree.
        """
        suffix = text if text.rstrip().endswith((";", "}")) else text + ";"
        document = CppDocument.parse(
            f"void __xr_stmt() {{ {suffix} }}",
            parser=self.parser,
        )
        body = document.nodes("compound_statement")[0]
        for child in body.named_children:
            return child.green
        raise ValueError("statement did not produce syntax")

    def declaration(self, text: str) -> GreenElement:
        """解析一条顶层声明并返回对应 green 元素。
        Parse and return one top-level declaration syntax subtree.
        """
        source = text if text.rstrip().endswith((";", "}")) else text + ";"
        document = CppDocument.parse(source, parser=self.parser)
        for child in document.root.named_children:
            return child.green
        raise ValueError("declaration did not produce syntax")

    def call_statement(
        self,
        callee: str,
        arguments: Iterable[str],
    ) -> GreenElement:
        """通过布局 IR 创建一条调用语句，并重新解析成结构化 green 元素。
        Build a function-call statement using the shared layout IR for argument wrapping.
        """
        document = Group(
            concat(
                callee,
                "(",
                Indent(
                    concat(
                        softline,
                        join(concat(",", line), tuple(arguments)),
                    )
                ),
                softline,
                ");",
            )
        )
        return self.statement(render(document, width=self.width))

    def variable(
        self,
        cpp_type: str,
        name: str,
        *,
        initializer: str | None = None,
        storage: Iterable[str] = (),
    ) -> GreenElement:
        """由类型、名称、存储类和初始化器创建变量声明。
        Build a simple variable declaration from common structured components.
        """
        prefix = " ".join((*storage, cpp_type, name))
        if initializer is not None:
            prefix += f" = {initializer}"
        return self.declaration(prefix)

    def function(
        self,
        return_type: str,
        name: str,
        *,
        parameters: Iterable[tuple[str, str]] = (),
        body: Iterable[str] = (),
        prefix: Iterable[str] = (),
    ) -> GreenElement:
        """由返回类型、名称、参数和 body 创建完整函数定义。
        Build a function definition from signature components and body statements.
        """
        params = ", ".join(f"{typ} {param}" for typ, param in parameters)
        lines = list(body)
        start = " ".join((*prefix, return_type, f"{name}({params})")).strip()
        if lines:
            body_text = "\n".join("  " + statement for statement in lines)
            source = f"{start} {{\n{body_text}\n}}"
        else:
            source = f"{start} {{}}"
        return self._first(source, "function_definition").green

    @staticmethod
    def _region(
        kind: str,
        begin: str,
        end: str,
        body: Iterable[GreenElement],
    ) -> GreenElement:
        """按给定 begin/end 标记和 body 统一构造一对保护区域。
        Construct one protected region from the given begin/end markers and body.
        """
        children: list[GreenChild] = [
            GreenChild(GreenToken("comment", begin, named=True)),
            GreenChild(GreenTrivia("newline", "\n")),
        ]
        for element in body:
            children.append(GreenChild(element))
            children.append(GreenChild(GreenTrivia("newline", "\n")))
        children.append(GreenChild(GreenToken("comment", end, named=True)))
        return GreenNode(kind, tuple(children), named=True)

    def _first(self, source: str, kind: str) -> SyntaxNode:
        """从临时解析结果中取得指定 kind 的第一个元素，缺失时抛出错误。
        Return the first parsed element of the requested kind, raising an error when it is absent.
        """
        document = CppDocument.parse(source, parser=self.parser)
        nodes = document.nodes(kind)
        if not nodes:
            raise ValueError(f"generated fragment did not contain {kind}")
        return nodes[0]
