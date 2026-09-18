"""Immutable position-independent syntax storage used as the persistent tree representation."""

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
    """Immutable source text that is not represented as a parser syntax child.

    Whitespace and byte gaps are kept explicitly so rendering a complete green tree
    can reproduce the original source byte-for-byte.
    """
    kind: str
    text: str

    def render(self) -> str:
        """Render this represented source without normalization."""
        return self.text

    @property
    def byte_width(self) -> int:
        """Return the encoded source width in bytes."""
        return len(encode_source(self.text))


@dataclass(frozen=True, slots=True)
class GreenToken(_GreenMixin):
    """Immutable leaf syntax element containing exactly the represented source text."""
    kind: str
    text: str
    named: bool = False
    missing: bool = False
    error: bool = False

    def render(self) -> str:
        """Render this represented source without normalization."""
        return self.text

    @property
    def byte_width(self) -> int:
        """Return the encoded source width in bytes."""
        return len(encode_source(self.text))


GreenElement: TypeAlias = "GreenNode | GreenToken | GreenTrivia"


@dataclass(frozen=True, slots=True)
class GreenChild:
    """One child edge in a green node, including the parser field name when available."""
    element: GreenElement
    field: str | None = None


@dataclass(frozen=True)
class GreenNode(_GreenMixin):
    """Immutable, position-independent syntax node.

    Green nodes deliberately store no parent pointer or absolute offset. That makes
    them safe to share across immutable snapshots and lets low-level rewrites reuse
    unchanged subtrees.
    """
    kind: str
    children: tuple[GreenChild, ...]
    named: bool = True
    missing: bool = False
    error: bool = False

    def render(self) -> str:
        """Render this represented source without normalization."""
        return "".join(child.element.render() for child in self.children)

    @cached_property
    def byte_width(self) -> int:
        """Return the encoded source width in bytes."""
        return sum(child.element.byte_width for child in self.children)

    def replacing_child(self, index: int, element: GreenElement) -> GreenNode:
        """Return a copy with one child replaced while preserving that edge's field label."""
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
        """Return a copy with a new child inserted at the requested structural index."""
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
        """Return a copy without the selected child."""
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
