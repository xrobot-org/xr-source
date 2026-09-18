from __future__ import annotations

from xr_source.core import SyntaxDocument, SyntaxElement, SyntaxNode

from .grammar import CMAKE_GRAMMAR
from .parser import CMakeParser
from .view import CMakeCommandView


class CMakeDocument(SyntaxDocument):
    __slots__ = ()

    language = "cmake"
    grammar = CMAKE_GRAMMAR

    @classmethod
    def parse(
        cls,
        source: str | bytes,
        *,
        source_name: str | None = None,
        parser: CMakeParser | None = None,
    ) -> CMakeDocument:
        selected = parser or CMakeParser()
        return cls(
            selected.parse(source, source_name=source_name),
            selected,
        )

    def comments(self) -> tuple[SyntaxElement, ...]:
        return self.elements("comment")

    def commands(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        nodes = tuple(
            node
            for node in self.root.descendants(include_self=True)
            if isinstance(node, SyntaxNode)
            and (node.kind == "normal_command" or node.kind.endswith("_command"))
        )
        if name is None:
            return nodes
        normalized = name.casefold()
        return tuple(
            node
            for node in nodes
            if CMakeCommandView(node).name.casefold() == normalized
        )

    def command_views(self, name: str | None = None) -> tuple[CMakeCommandView, ...]:
        return tuple(CMakeCommandView(node) for node in self.commands(name))

    def blocks(self) -> tuple[SyntaxNode, ...]:
        kinds = {
            "if_condition",
            "foreach_loop",
            "while_loop",
            "function_def",
            "macro_def",
        }
        return tuple(
            node
            for node in self.root.descendants(include_self=True)
            if isinstance(node, SyntaxNode) and node.kind in kinds
        )
