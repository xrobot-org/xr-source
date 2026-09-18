"""提供 CMake 命令与参数的轻量只读视图，保留原始源码文本和语法节点。"""

from __future__ import annotations

from dataclasses import dataclass

from xr_source.core import SyntaxElement, SyntaxNode


@dataclass(frozen=True, slots=True)
class CMakeArgumentView:
    """表示一个 CMake 参数的便捷视图，同时保留其原始语法文本。"""
    node: SyntaxElement

    @property
    def text(self) -> str:
        """返回该参数在源码中的精确文本。"""
        return self.node.text

    @property
    def syntax_kind(self) -> str:
        """返回该参数视图所代表的最具体 named syntax kind。"""
        if isinstance(self.node, SyntaxNode):
            child = next(iter(self.node.named_syntax_children), None)
            if child is not None:
                return child.kind
        return self.node.kind


@dataclass(frozen=True, slots=True)
class CMakeCommandView:
    """统一普通命令和块命令的名称与参数访问方式。"""
    node: SyntaxNode

    @property
    def name(self) -> str:
        """返回普通命令或块命令统一后的命令名。"""
        if self.node.kind == "normal_command":
            for child in self.node.named_syntax_children:
                if child.kind == "identifier":
                    return child.text
        for child in self.node.syntax_children:
            if child.kind not in {"argument_list", "(", ")"}:
                return child.text
        return self.node.kind.removesuffix("_command")

    @property
    def arguments(self) -> tuple[CMakeArgumentView, ...]:
        """按源码顺序返回该命令的参数视图。"""
        argument_list = self.node.first_descendant("argument_list")
        if not isinstance(argument_list, SyntaxNode):
            return ()
        return tuple(
            CMakeArgumentView(child)
            for child in argument_list.named_syntax_children
            if child.kind == "argument"
        )
