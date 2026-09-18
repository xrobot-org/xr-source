"""Parent-aware, position-aware views over immutable green syntax elements."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .green import GreenChild, GreenElement, GreenNode, GreenToken, GreenTrivia
from .span import SourceSpan

if TYPE_CHECKING:
    from .tree import SyntaxTree


class SyntaxElement:
    """Snapshot-specific view that adds parent, field, index and byte offset to a green element.

    A red element must never be reused with a different SyntaxTree snapshot; its
    path and offset are meaningful only in the tree that created it.
    """
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
        """Return the owning syntax-tree snapshot."""
        return self._tree

    @property
    def green(self) -> GreenElement:
        """Return the wrapped immutable green element."""
        return self._green

    @property
    def parent(self) -> SyntaxNode | None:
        """Return the parent syntax node, or None for the root."""
        return self._parent

    @property
    def index(self) -> int:
        """Return this element's structural child index."""
        return self._index

    @property
    def field(self) -> str | None:
        """Return the parser field label on the parent edge, when present."""
        return self._field

    @property
    def kind(self) -> str:
        """Return the parser syntax-kind spelling."""
        return self._green.kind

    @property
    def span(self) -> SourceSpan:
        """Return this element's half-open source byte span."""
        return SourceSpan(self._offset, self._offset + self._green.byte_width)

    @property
    def text(self) -> str:
        """Wrap literal text as a layout document."""
        return self._green.render()

    @property
    def path(self) -> tuple[int, ...]:
        # A path is snapshot-relative: it identifies structural child indices,
        # not a stable identity that may be carried across edited documents.
        """Return the source spelling of this path."""
        if self._parent is None:
            return ()
        return self._parent.path + (self._index,)

    @property
    def is_node(self) -> bool:
        """Report whether this element wraps a syntax node."""
        return isinstance(self._green, GreenNode)

    @property
    def is_token(self) -> bool:
        """Report whether this element wraps a syntax token."""
        return isinstance(self._green, GreenToken)

    @property
    def is_trivia(self) -> bool:
        """Report whether this element wraps preserved trivia."""
        return isinstance(self._green, GreenTrivia)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(kind={self.kind!r}, span={self.span!r})"


class SyntaxNode(SyntaxElement):
    """Parent-aware view of a GreenNode with traversal and field-query helpers."""

    @property
    def green(self) -> GreenNode:
        """Return the wrapped immutable green element."""
        return self._green  # type: ignore[return-value]

    @property
    def named(self) -> bool:
        """Return the parser's named-versus-anonymous classification."""
        return self.green.named

    @property
    def missing(self) -> bool:
        """Report whether parser recovery synthesized this element."""
        return self.green.missing

    @property
    def error(self) -> bool:
        """Report whether this element is marked as parser error recovery."""
        return self.green.error

    @property
    def children(self) -> tuple[SyntaxElement, ...]:
        """Materialize red child views and derive their absolute byte offsets in source order."""
        result: list[SyntaxElement] = []
        # Absolute positions are derived here from immutable child widths rather
        # than stored in green nodes. This is what keeps green subtrees reusable.
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
        """Return parser syntax children while excluding xr-source trivia gap objects."""
        return tuple(child for child in self.children if not child.is_trivia)

    @property
    def named_syntax_children(self) -> tuple[SyntaxElement, ...]:
        """Return named parser nodes/tokens, excluding anonymous punctuation and trivia."""
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
        """Return named child nodes only."""
        return tuple(
            child
            for child in self.named_syntax_children
            if isinstance(child, SyntaxNode)
        )

    def child_by_field(self, field: str) -> SyntaxElement | None:
        """Return the first child carried by a parser field with this name."""
        return next((child for child in self.children if child.field == field), None)

    def children_by_field(self, field: str) -> tuple[SyntaxElement, ...]:
        """Return all children carried by a repeated parser field."""
        return tuple(child for child in self.children if child.field == field)

    @property
    def field_names(self) -> tuple[str, ...]:
        """Return field labels present on this syntax node."""
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
        """Depth-first traversal of descendants with optional kind/trivia filtering."""
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
        """Return the first depth-first descendant of the requested kind."""
        return next(self.descendants(kind), None)


class SyntaxToken(SyntaxElement):
    """Red view of an immutable syntax token."""

    @property
    def green(self) -> GreenToken:
        """Return the wrapped immutable green element."""
        return self._green  # type: ignore[return-value]

    @property
    def named(self) -> bool:
        """Return the parser's named-versus-anonymous classification."""
        return self.green.named

    @property
    def missing(self) -> bool:
        """Report whether parser recovery synthesized this element."""
        return self.green.missing

    @property
    def error(self) -> bool:
        """Report whether this element is marked as parser error recovery."""
        return self.green.error


class SyntaxTrivia(SyntaxElement):
    """Red view of preserved source trivia that the parser did not expose as syntax."""

    @property
    def green(self) -> GreenTrivia:
        """Return the wrapped immutable green element."""
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
