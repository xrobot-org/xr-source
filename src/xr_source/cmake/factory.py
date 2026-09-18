"""Factories for creating parser-backed CMake command and block fragments."""

from __future__ import annotations

from collections.abc import Iterable

from xr_source.core import GreenElement, GreenToken, SyntaxNode
from xr_source.format import Group, Indent, concat, join, line, render, softline

from .document import CMakeDocument
from .parser import CMakeParser


class CMakeFactory:
    """Create parser-backed CMake fragments using the shared layout IR."""
    def __init__(
        self,
        parser: CMakeParser | None = None,
        *,
        width: int = 100,
    ) -> None:
        self.parser = parser or CMakeParser()
        self.width = width

    def raw(self, source: str) -> GreenElement:
        """Create opaque CMake source when a typed command helper is inappropriate."""
        return GreenToken("raw", source, named=True)

    def comment(self, text: str) -> GreenElement:
        """Create one CMake line-comment fragment."""
        return self._first(f"# {text}\n", "comment").green

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> GreenElement:
        """Create one CMake command with width-aware argument layout."""
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
        """Create a complete if()/endif() block from structured condition/body fragments."""
        opening = self.command("if", condition).render().rstrip("\r\n")
        closing = "endif()"
        body_text = "".join(element.render() for element in body)
        if body_text and not body_text.endswith(("\n", "\r")):
            body_text += "\n"
        source = f"{opening}\n{body_text}{closing}\n"
        return self._first(source, "if_condition").green

    def _first(self, source: str, kind: str) -> SyntaxNode:
        document = CMakeDocument.parse(source, parser=self.parser)
        nodes = document.nodes(kind)
        if not nodes:
            raise ValueError(f"generated CMake fragment did not contain {kind}")
        return nodes[0]
