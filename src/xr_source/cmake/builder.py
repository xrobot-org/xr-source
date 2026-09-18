"""Structured builder for complete CMake source files."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from xr_source.core import GreenElement

from .document import CMakeDocument
from .factory import CMakeFactory


@dataclass(slots=True)
class CMakeFileBuilder:
    """Top-level builder for complete CMake files using parser-backed fragments."""
    factory: CMakeFactory = field(default_factory=CMakeFactory)
    items: list[GreenElement] = field(default_factory=list)

    def add(self, element: GreenElement) -> GreenElement:
        """Append the element to this builder and return it."""
        self.items.append(element)
        return element

    def raw(self, source: str) -> GreenElement:
        """Append or create opaque source text without interpreting its internal structure."""
        return self.add(self.factory.raw(source))

    def comment(self, text: str) -> GreenElement:
        """Append or create a source comment."""
        return self.add(self.factory.comment(text))

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> GreenElement:
        """Create and append one command."""
        return self.add(self.factory.command(name, arguments))

    def if_block(
        self,
        condition: Iterable[str],
        body: Iterable[GreenElement],
    ) -> GreenElement:
        """Create and append one complete conditional block."""
        return self.add(self.factory.if_block(condition, body))

    def build(self) -> CMakeDocument:
        """Render all fragments and parse the complete source back into CMakeDocument."""
        rendered = [item.render().rstrip("\r\n") for item in self.items]
        source = "\n".join(rendered)
        if source and not source.endswith("\n"):
            source += "\n"
        return CMakeDocument.parse(source, parser=self.factory.parser)
