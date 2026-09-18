"""提供 CMake 命令、注释和条件块的 parser-backed 片段工厂。"""

from __future__ import annotations

from collections.abc import Iterable

from xr_source.core import GreenElement, GreenToken, SyntaxNode
from xr_source.format import Group, Indent, concat, join, line, render, softline

from .document import CMakeDocument
from .parser import CMakeParser


class CMakeFactory:
    """利用共享布局 IR 创建可重新解析的 CMake 命令、注释和块结构。"""
    def __init__(
        self,
        parser: CMakeParser | None = None,
        *,
        width: int = 100,
    ) -> None:
        """初始化 CMake 片段工厂并保存布局宽度配置。"""
        self.parser = parser or CMakeParser()
        self.width = width

    def raw(self, source: str) -> GreenElement:
        """创建不做结构解释的原始 CMake 片段。"""
        return GreenToken("raw", source, named=True)

    def comment(self, text: str) -> GreenElement:
        """创建一条 CMake 行注释片段。"""
        return self._first(f"# {text}\n", "comment").green

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> GreenElement:
        """按给定宽度用布局 IR 创建一个 CMake 命令。"""
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
        return self._first(source, "normal_command").green

    def if_block(
        self,
        condition: Iterable[str],
        body: Iterable[GreenElement],
    ) -> GreenElement:
        """由结构化条件和 body 片段创建完整 if()/endif() 块。"""
        opening = self.command("if", condition).render().rstrip("\r\n")
        closing = "endif()"
        body_text = "".join(element.render() for element in body)
        if body_text and not body_text.endswith(("\n", "\r")):
            body_text += "\n"
        source = f"{opening}\n{body_text}{closing}\n"
        return self._first(source, "if_condition").green

    def _first(self, source: str, kind: str) -> SyntaxNode:
        """从临时解析结果中取得指定 kind 的第一个节点，缺失时抛出错误。"""
        document = CMakeDocument.parse(source, parser=self.parser)
        nodes = document.nodes(kind)
        if not nodes:
            raise ValueError(f"generated CMake fragment did not contain {kind}")
        return nodes[0]
