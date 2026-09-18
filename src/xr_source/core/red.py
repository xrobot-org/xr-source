from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .green import GreenChild, GreenElement, GreenNode, GreenToken, GreenTrivia
from .span import SourceSpan

if TYPE_CHECKING:
    from .tree import SyntaxTree


class SyntaxElement:
    __slots__ = ("_tree", "_green", "_parent", "_index", "_offset", "_field")

    def __init__(
        self,
        tree: SyntaxTree,
        green: GreenElement,
        *,
        parent: SyntaxNode | None,
        index: int,
        offset: int,
        field: str | None,
    ) -> None:
        self._tree = tree
        self._green = green
        self._parent = parent
        self._index = index
        self._offset = offset
        self._field = field

    @property
    def tree(self) -> SyntaxTree:
        return self._tree

    @property
    def green(self) -> GreenElement:
        return self._green

    @property
    def parent(self) -> SyntaxNode | None:
        return self._parent

    @property
    def index(self) -> int:
        return self._index

    @property
    def field(self) -> str | None:
        return self._field

    @property
    def kind(self) -> str:
        return self._green.kind

    @property
    def span(self) -> SourceSpan:
        return SourceSpan(self._offset, self._offset + self._green.byte_width)

    @property
    def text(self) -> str:
        return self._green.render()

    @property
    def path(self) -> tuple[int, ...]:
        if self._parent is None:
            return ()
        return self._parent.path + (self._index,)

    @property
    def is_node(self) -> bool:
        return isinstance(self._green, GreenNode)

    @property
    def is_token(self) -> bool:
        return isinstance(self._green, GreenToken)

    @property
    def is_trivia(self) -> bool:
        return isinstance(self._green, GreenTrivia)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(kind={self.kind!r}, span={self.span!r})"


class SyntaxNode(SyntaxElement):
    @property
    def green(self) -> GreenNode:
        return self._green  # type: ignore[return-value]

    @property
    def named(self) -> bool:
        return self.green.named

    @property
    def missing(self) -> bool:
        return self.green.missing

    @property
    def error(self) -> bool:
        return self.green.error

    @property
    def children(self) -> tuple[SyntaxElement, ...]:
        result: list[SyntaxElement] = []
        offset = self._offset
        for index, child in enumerate(self.green.children):
            result.append(
                _wrap(
                    self._tree,
                    child,
                    parent=self,
                    index=index,
                    offset=offset,
                )
            )
            offset += child.element.byte_width
        return tuple(result)

    @property
    def syntax_children(self) -> tuple[SyntaxElement, ...]:
        return tuple(child for child in self.children if not child.is_trivia)

    @property
    def named_syntax_children(self) -> tuple[SyntaxElement, ...]:
        return tuple(
            child
            for child in self.syntax_children
            if (
                isinstance(child, (SyntaxNode, SyntaxToken))
                and child.named
            )
        )

    @property
    def named_children(self) -> tuple[SyntaxNode, ...]:
        return tuple(
            child
            for child in self.named_syntax_children
            if isinstance(child, SyntaxNode)
        )

    def child_by_field(self, field: str) -> SyntaxElement | None:
        return next((child for child in self.children if child.field == field), None)

    def children_by_field(self, field: str) -> tuple[SyntaxElement, ...]:
        return tuple(child for child in self.children if child.field == field)

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                child.field for child in self.children if child.field is not None
            )
        )

    def descendants(
        self,
        kind: str | None = None,
        *,
        include_self: bool = False,
        include_trivia: bool = False,
    ) -> Iterator[SyntaxElement]:
        if include_self and (kind is None or self.kind == kind):
            yield self
        for child in self.children:
            if child.is_trivia and not include_trivia:
                continue
            if kind is None or child.kind == kind:
                yield child
            if isinstance(child, SyntaxNode):
                yield from child.descendants(kind, include_trivia=include_trivia)

    def first_descendant(self, kind: str) -> SyntaxElement | None:
        return next(self.descendants(kind), None)


class SyntaxToken(SyntaxElement):
    @property
    def green(self) -> GreenToken:
        return self._green  # type: ignore[return-value]

    @property
    def named(self) -> bool:
        return self.green.named

    @property
    def missing(self) -> bool:
        return self.green.missing

    @property
    def error(self) -> bool:
        return self.green.error


class SyntaxTrivia(SyntaxElement):
    @property
    def green(self) -> GreenTrivia:
        return self._green  # type: ignore[return-value]


def _wrap(
    tree: SyntaxTree,
    child: GreenChild,
    *,
    parent: SyntaxNode | None,
    index: int,
    offset: int,
) -> SyntaxElement:
    green = child.element
    if isinstance(green, GreenNode):
        return SyntaxNode(
            tree,
            green,
            parent=parent,
            index=index,
            offset=offset,
            field=child.field,
        )
    if isinstance(green, GreenToken):
        return SyntaxToken(
            tree,
            green,
            parent=parent,
            index=index,
            offset=offset,
            field=child.field,
        )
    return SyntaxTrivia(
        tree,
        green,
        parent=parent,
        index=index,
        offset=offset,
        field=child.field,
    )
