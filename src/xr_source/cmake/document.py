"""High-level CMake document queries over the generic syntax model."""

from __future__ import annotations

from xr_source.core import SyntaxDocument, SyntaxElement, SyntaxNode

from .grammar import CMAKE_GRAMMAR
from .parser import CMakeParser
from .view import CMakeCommandView


class CMakeDocument(SyntaxDocument):
    """CMake-specific query facade over the same immutable syntax core used by C++."""
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
        """Parse CMake source using the optional pinned language-pack grammar."""
        selected = parser or CMakeParser()
        return cls(
            selected.parse(source, source_name=source_name),
            selected,
        )

    def comments(self) -> tuple[SyntaxElement, ...]:
        """Return CMake comments in source order."""
        return self.elements("comment")

    def commands(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        """Return command nodes, optionally filtered case-insensitively by command name."""
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
        """Return typed command views, optionally filtered by command name."""
        return tuple(CMakeCommandView(node) for node in self.commands(name))

    def blocks(self) -> tuple[SyntaxNode, ...]:
        """Return structured block nodes such as if/foreach/while/function/macro constructs."""
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
