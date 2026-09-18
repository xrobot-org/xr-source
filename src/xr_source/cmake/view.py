"""Convenience views for CMake commands and arguments."""

from __future__ import annotations

from dataclasses import dataclass

from xr_source.core import SyntaxElement, SyntaxNode


@dataclass(frozen=True, slots=True)
class CMakeArgumentView:
    """Convenience view of one CMake argument while retaining its original syntax text."""
    node: SyntaxElement

    @property
    def text(self) -> str:
        """Wrap literal text as a layout document."""
        return self.node.text

    @property
    def syntax_kind(self) -> str:
        """Return the most specific named syntax kind represented by this view."""
        if isinstance(self.node, SyntaxNode):
            child = next(iter(self.node.named_syntax_children), None)
            if child is not None:
                return child.kind
        return self.node.kind


@dataclass(frozen=True, slots=True)
class CMakeCommandView:
    """Convenience view that normalizes the name/arguments of normal and block commands."""
    node: SyntaxNode

    @property
    def name(self) -> str:
        """Return normalized command spelling for normal or block command nodes."""
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
        """Return typed argument views in source order."""
        argument_list = self.node.first_descendant("argument_list")
        if not isinstance(argument_list, SyntaxNode):
            return ()
        return tuple(
            CMakeArgumentView(child)
            for child in argument_list.named_syntax_children
            if child.kind == "argument"
        )
