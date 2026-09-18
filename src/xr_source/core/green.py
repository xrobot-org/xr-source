from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TypeAlias

from .text import encode_source


class _GreenMixin:
    def render(self) -> str:
        raise NotImplementedError

    @property
    def byte_width(self) -> int:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class GreenTrivia(_GreenMixin):
    kind: str
    text: str

    def render(self) -> str:
        return self.text

    @property
    def byte_width(self) -> int:
        return len(encode_source(self.text))


@dataclass(frozen=True, slots=True)
class GreenToken(_GreenMixin):
    kind: str
    text: str
    named: bool = False
    missing: bool = False
    error: bool = False

    def render(self) -> str:
        return self.text

    @property
    def byte_width(self) -> int:
        return len(encode_source(self.text))


GreenElement: TypeAlias = "GreenNode | GreenToken | GreenTrivia"


@dataclass(frozen=True, slots=True)
class GreenChild:
    element: GreenElement
    field: str | None = None


@dataclass(frozen=True)
class GreenNode(_GreenMixin):
    kind: str
    children: tuple[GreenChild, ...]
    named: bool = True
    missing: bool = False
    error: bool = False

    def render(self) -> str:
        return "".join(child.element.render() for child in self.children)

    @cached_property
    def byte_width(self) -> int:
        return sum(child.element.byte_width for child in self.children)

    def replacing_child(self, index: int, element: GreenElement) -> GreenNode:
        if index < 0 or index >= len(self.children):
            raise IndexError(index)
        children = list(self.children)
        original = children[index]
        children[index] = GreenChild(element=element, field=original.field)
        return GreenNode(
            kind=self.kind,
            children=tuple(children),
            named=self.named,
            missing=self.missing,
            error=self.error,
        )

    def inserting_child(
        self,
        index: int,
        element: GreenElement,
        *,
        field: str | None = None,
    ) -> GreenNode:
        if index < 0 or index > len(self.children):
            raise IndexError(index)
        children = list(self.children)
        children.insert(index, GreenChild(element=element, field=field))
        return GreenNode(
            kind=self.kind,
            children=tuple(children),
            named=self.named,
            missing=self.missing,
            error=self.error,
        )

    def removing_child(self, index: int) -> GreenNode:
        if index < 0 or index >= len(self.children):
            raise IndexError(index)
        children = list(self.children)
        del children[index]
        return GreenNode(
            kind=self.kind,
            children=tuple(children),
            named=self.named,
            missing=self.missing,
            error=self.error,
        )
