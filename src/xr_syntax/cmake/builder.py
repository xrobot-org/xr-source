"""提供完整 CMake 文件的结构化构建器，并把生成结果重新解析为统一的语法模型。
Structured builder for complete CMake source files.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from xr_syntax.core import SyntaxFragment

from .document import CMakeDocument
from .factory import CMakeFactory


@dataclass
class CMakeFileBuilder:
    """用于按源码顺序累积 CMake 片段并最终构建完整 CMakeDocument 的顶层构建器。
    Top-level builder for complete CMake files using parser-backed fragments.
    """
    factory: CMakeFactory = field(default_factory=CMakeFactory)
    items: list[SyntaxFragment] = field(default_factory=list)

    def add(self, element: SyntaxFragment) -> SyntaxFragment:
        """把一个语法元素追加到当前文件构建器，并返回该元素便于继续组合。
        Append the element to this builder and return it.
        """
        self.items.append(element)
        return element

    def raw(self, source: str) -> SyntaxFragment:
        """追加一段不解释内部结构的原始 CMake 源码。
        Append or create opaque source text without interpreting its internal structure.
        """
        return self.add(self.factory.raw(source))

    def comment(self, text: str) -> SyntaxFragment:
        """创建并追加一条 CMake 行注释。
        Append or create a source comment.
        """
        return self.add(self.factory.comment(text))

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> SyntaxFragment:
        """创建并追加一个 CMake 命令。
        Create and append one command.
        """
        return self.add(self.factory.command(name, arguments))

    def if_block(
        self,
        condition: Iterable[str],
        body: Iterable[SyntaxFragment],
    ) -> SyntaxFragment:
        """创建并追加一个完整的 if()/endif() 条件块。
        Create and append one complete conditional block.
        """
        return self.add(self.factory.if_block(condition, body))

    def build(self) -> CMakeDocument:
        """渲染已累积片段，再重新解析为完整的 CMakeDocument。
        Render all fragments and parse the complete source back into CMakeDocument.
        """
        rendered = [item.render().rstrip("\r\n") for item in self.items]
        source = "\n".join(rendered)
        if source and not source.endswith("\n"):
            source += "\n"
        return CMakeDocument.parse(source, parser=self.factory.parser)
