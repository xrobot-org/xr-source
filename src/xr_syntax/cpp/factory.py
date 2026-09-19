"""提供常见 C++ 源码片段的 parser-backed 工厂。
Factories for parser-backed C++ source fragments.
"""

from __future__ import annotations

from collections.abc import Iterable

from xr_syntax.core import (
    GreenChild,
    GreenNode,
    GreenToken,
    GreenTrivia,
    SyntaxElement,
    SyntaxFragment,
    SyntaxNode,
)
from xr_syntax.format import Group, Indent, concat, join, line, render, softline

from .document import CppDocument
from .parser import CppParser


class CppFactory:
    """创建带 C++ 语言归属的 parser-backed 片段。
    Create parser-backed fragments carrying explicit C++ language provenance.
    """

    language = "cpp"

    def __init__(self, parser: CppParser | None = None, *, width: int = 100) -> None:
        """初始化片段工厂并保存布局宽度。
        Initialize the fragment factory and store its layout width.
        """
        self.parser = parser or CppParser()
        self.width = width

    def include(self, header: str, *, system: bool = False) -> SyntaxFragment:
        """创建 include 指令片段。
        Create one include-directive fragment.
        """
        delimiters = ("<", ">") if system else ('"', '"')
        source = f"#include {delimiters[0]}{header}{delimiters[1]}\n"
        return self._fragment(self._first(source, "preproc_include"))

    def comment(self, text: str, *, block: bool = False) -> SyntaxFragment:
        """创建行注释或块注释片段。
        Create one line-comment or block-comment fragment.
        """
        source = f"/* {text} */" if block else f"// {text}"
        return self._fragment(self._first(source, "comment"))

    def directive(self, source: str) -> SyntaxFragment:
        """创建预处理指令片段。
        Create and validate one preprocessor-directive fragment.
        """
        document = CppDocument.parse(source.rstrip() + "\n", parser=self.parser)
        for child in document.root.syntax_children:
            return self._fragment(child)
        raise ValueError("directive did not produce syntax")

    def raw(self, source: str) -> SyntaxFragment:
        """创建显式 opaque 的原始 C++ 片段。
        Create an explicit opaque C++ source fragment.
        """
        return SyntaxFragment(
            self.language,
            GreenToken("raw", source, named=True),
            opaque=True,
        )

    def user_region(
        self,
        name: str,
        body: Iterable[SyntaxFragment] = (),
    ) -> SyntaxFragment:
        """创建 User Code Begin/End 区域。
        Create a paired User Code region.
        """
        return self._region(
            "xr_user_region",
            f"/* User Code Begin {name} */",
            f"/* User Code End {name} */",
            body,
        )

    def format_region(self, body: Iterable[SyntaxFragment]) -> SyntaxFragment:
        """创建 clang-format off/on 区域。
        Create a paired clang-format off/on region.
        """
        return self._region(
            "xr_format_region",
            "// clang-format off",
            "// clang-format on",
            body,
        )

    def lint_region(self, body: Iterable[SyntaxFragment]) -> SyntaxFragment:
        """创建 NOLINTBEGIN/NOLINTEND 区域。
        Create a paired NOLINTBEGIN/NOLINTEND region.
        """
        return self._region(
            "xr_lint_region",
            "// NOLINTBEGIN",
            "// NOLINTEND",
            body,
        )

    def expression(self, text: str) -> SyntaxFragment:
        """解析一个表达式片段。
        Parse one expression fragment in a temporary function context.
        """
        document = CppDocument.parse(
            f"auto __xr_expr() -> decltype(auto) {{ return {text}; }}",
            parser=self.parser,
        )
        statement = document.nodes("return_statement")[0]
        for child in statement.named_children:
            return self._fragment(child)
        raise ValueError("expression did not produce syntax")

    def statement(self, text: str) -> SyntaxFragment:
        """解析一个语句片段。
        Parse one statement fragment in a temporary function body.
        """
        suffix = text if text.rstrip().endswith((";", "}")) else text + ";"
        document = CppDocument.parse(
            f"void __xr_stmt() {{ {suffix} }}",
            parser=self.parser,
        )
        body = document.nodes("compound_statement")[0]
        for child in body.named_children:
            return self._fragment(child)
        raise ValueError("statement did not produce syntax")

    def declaration(self, text: str) -> SyntaxFragment:
        """解析一个顶层声明片段。
        Parse one top-level declaration fragment.
        """
        source = text if text.rstrip().endswith((";", "}")) else text + ";"
        document = CppDocument.parse(source, parser=self.parser)
        for child in document.root.named_children:
            return self._fragment(child)
        raise ValueError("declaration did not produce syntax")

    def call_statement(
        self,
        callee: str,
        arguments: Iterable[str],
    ) -> SyntaxFragment:
        """通过布局 IR 创建函数调用语句。
        Build a function-call statement through the shared layout IR.
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
    ) -> SyntaxFragment:
        """由常用字段创建变量声明片段。
        Build a variable-declaration fragment from common structured fields.
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
    ) -> SyntaxFragment:
        """由签名和 body 创建函数定义片段。
        Build a function-definition fragment from a signature and body statements.
        """
        params = ", ".join(f"{typ} {param}" for typ, param in parameters)
        lines = list(body)
        start = " ".join((*prefix, return_type, f"{name}({params})")).strip()
        if lines:
            body_text = "\n".join("  " + statement for statement in lines)
            source = f"{start} {{\n{body_text}\n}}"
        else:
            source = f"{start} {{}}"
        return self._fragment(self._first(source, "function_definition"))

    def _region(
        self,
        kind: str,
        begin: str,
        end: str,
        body: Iterable[SyntaxFragment],
    ) -> SyntaxFragment:
        """按 begin/end 标记构造保护区域。
        Construct a protected region from begin/end markers and body fragments.
        """
        children: list[GreenChild] = [
            GreenChild(GreenToken("comment", begin, named=True)),
            GreenChild(GreenTrivia("newline", "\n")),
        ]
        for fragment in body:
            children.append(GreenChild(fragment.green_for(self.language)))
            children.append(GreenChild(GreenTrivia("newline", "\n")))
        children.append(GreenChild(GreenToken("comment", end, named=True)))
        return SyntaxFragment(
            self.language,
            GreenNode(kind, tuple(children), named=True),
        )

    def _fragment(self, element: SyntaxElement) -> SyntaxFragment:
        """把解析得到的元素包装成 C++ fragment。
        Wrap one parsed syntax element as a C++ fragment.
        """
        return SyntaxFragment(self.language, element.green)

    def _first(self, source: str, kind: str) -> SyntaxNode:
        """返回临时解析结果中指定 kind 的第一个节点。
        Return the first parsed node of the requested kind.
        """
        document = CppDocument.parse(source, parser=self.parser)
        nodes = document.nodes(kind)
        if not nodes:
            raise ValueError(f"generated fragment did not contain {kind}")
        return nodes[0]
