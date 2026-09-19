"""提供 CMake 命令、注释和条件块的 parser-backed 片段工厂。
Factories for parser-backed CMake source fragments.
"""

from __future__ import annotations

from collections.abc import Iterable

from xr_syntax.core import GreenToken, SyntaxFragment, SyntaxNode
from xr_syntax.format import Group, Indent, concat, join, line, render, softline

from .document import CMakeDocument
from .parser import CMakeParser


class CMakeFactory:
    """创建带 CMake 语言归属的 parser-backed 片段。
    Create parser-backed fragments carrying explicit CMake language provenance.
    """

    language = "cmake"

    def __init__(
        self,
        parser: CMakeParser | None = None,
        *,
        width: int = 100,
    ) -> None:
        """初始化 CMake 片段工厂并保存布局宽度。
        Initialize the CMake fragment factory and store its layout width.
        """
        self.parser = parser or CMakeParser()
        self.width = width

    def raw(self, source: str) -> SyntaxFragment:
        """创建显式 opaque 的原始 CMake 片段。
        Create an explicit opaque CMake source fragment.
        """
        return SyntaxFragment(
            self.language,
            GreenToken("raw", source, named=True),
            opaque=True,
        )

    def comment(self, text: str) -> SyntaxFragment:
        """创建一条 CMake 行注释片段。
        Create one CMake line-comment fragment.
        """
        return self._fragment(self._first(f"# {text}\n", "comment"))

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> SyntaxFragment:
        """按给定宽度创建一个 CMake 命令片段。
        Create one CMake command fragment with width-aware argument layout.
        """
        document = Group(
            concat(
                name,
                "(",
                Indent(
                    concat(
                        softline,
                        join(line, tuple(arguments)),
                    )
                ),
                softline,
                ")",
            )
        )
        source = render(document, width=self.width) + "\n"
        return self._fragment(self._first(source, "normal_command"))

    def if_block(
        self,
        condition: Iterable[str],
        body: Iterable[SyntaxFragment],
    ) -> SyntaxFragment:
        """由条件和 body 片段创建 if()/endif() 块。
        Create a complete if()/endif() block from condition and body fragments.
        """
        opening = self.command("if", condition).render().rstrip("\r\n")
        closing = "endif()"
        body_text = "".join(fragment.green_for(self.language).render() for fragment in body)
        if body_text and not body_text.endswith(("\n", "\r")):
            body_text += "\n"
        source = f"{opening}\n{body_text}{closing}\n"
        return self._fragment(self._first(source, "if_condition"))

    def _fragment(self, node: SyntaxNode) -> SyntaxFragment:
        """把解析节点包装成 CMake fragment。
        Wrap one parsed node as a CMake syntax fragment.
        """
        return SyntaxFragment(self.language, node.green)

    def _first(self, source: str, kind: str) -> SyntaxNode:
        """返回临时解析结果中指定 kind 的第一个节点。
        Return the first parsed node of the requested kind.
        """
        document = CMakeDocument.parse(source, parser=self.parser)
        nodes = document.nodes(kind)
        if not nodes:
            raise ValueError(f"generated CMake fragment did not contain {kind}")
        return nodes[0]
