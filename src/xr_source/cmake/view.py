from __future__ import annotations

from dataclasses import dataclass

from xr_source.core import SyntaxElement, SyntaxNode


@dataclass(frozen=True, slots=True)
class CMakeArgumentView:
    node: SyntaxElement

    @property
    def text(self) -> str:
        return self.node.text

    @property
    def syntax_kind(self) -> str:
        if isinstance(self.node, SyntaxNode):
            child = next(iter(self.node.named_syntax_children), None)
            if child is not None:
                return child.kind
        return self.node.kind


@dataclass(frozen=True, slots=True)
class CMakeCommandView:
    node: SyntaxNode

    @property
    def name(self) -> str:
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
        argument_list = self.node.first_descendant("argument_list")
        if not isinstance(argument_list, SyntaxNode):
            return ()
        return tuple(
            CMakeArgumentView(child)
            for child in argument_list.named_syntax_children
            if child.kind == "argument"
        )
