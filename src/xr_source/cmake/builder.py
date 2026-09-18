from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from xr_source.core import GreenElement

from .document import CMakeDocument
from .factory import CMakeFactory


@dataclass(slots=True)
class CMakeFileBuilder:
    factory: CMakeFactory = field(default_factory=CMakeFactory)
    items: list[GreenElement] = field(default_factory=list)

    def add(self, element: GreenElement) -> GreenElement:
        self.items.append(element)
        return element

    def raw(self, source: str) -> GreenElement:
        return self.add(self.factory.raw(source))

    def comment(self, text: str) -> GreenElement:
        return self.add(self.factory.comment(text))

    def command(
        self,
        name: str,
        arguments: Iterable[str] = (),
    ) -> GreenElement:
        return self.add(self.factory.command(name, arguments))

    def if_block(
        self,
        condition: Iterable[str],
        body: Iterable[GreenElement],
    ) -> GreenElement:
        return self.add(self.factory.if_block(condition, body))

    def build(self) -> CMakeDocument:
        rendered = [item.render().rstrip("\r\n") for item in self.items]
        source = "\n".join(rendered)
        if source and not source.endswith("\n"):
            source += "\n"
        return CMakeDocument.parse(source, parser=self.factory.parser)
