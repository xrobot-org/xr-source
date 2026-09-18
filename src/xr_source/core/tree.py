"""Immutable syntax-tree snapshot and low-level structural edit operations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .diagnostic import Diagnostic
from .green import GreenChild, GreenElement, GreenNode, GreenTrivia
from .red import SyntaxElement, SyntaxNode
from .text import encode_source


@dataclass(frozen=True, slots=True)
class SyntaxTree:
    """Immutable language syntax snapshot backed by a green root.

    The tree owns diagnostics/source identity and creates red views on demand. Its
    edit methods are intentionally low-level: they preserve structural sharing but
    do not invoke the language parser again.
    """
    language: str
    green_root: GreenNode
    diagnostics: tuple[Diagnostic, ...] = ()
    source_name: str | None = None

    @property
    def root(self) -> SyntaxNode:
        """Create the red root view for this immutable snapshot."""
        return SyntaxNode(
            self,
            self.green_root,
            parent=None,
            index=0,
            offset=0,
            field=None,
        )

    def render(self) -> str:
        """Render the complete represented source without normalization."""
        return self.green_root.render()

    def render_bytes(self) -> bytes:
        """Render the complete represented source as bytes."""
        return encode_source(self.render())

    def replace(
        self,
        target: SyntaxElement,
        replacement: SyntaxElement | GreenElement,
    ) -> SyntaxTree:
        """Persistently replace one element, reusing unaffected green subtrees."""
        self._check_target(target)
        green = replacement.green if isinstance(replacement, SyntaxElement) else replacement
        if not target.path:
            if not isinstance(green, GreenNode):
                raise TypeError("syntax tree root must remain a GreenNode")
            return self._with_root(green)
        return self._with_root(_replace_at(self.green_root, target.path, green))

    def remove(self, target: SyntaxElement) -> SyntaxTree:
        """Persistently remove one non-root element."""
        self._check_target(target)
        if not target.path:
            raise ValueError("cannot remove the syntax tree root")
        return self._with_root(_remove_at(self.green_root, target.path))

    def insert_before(
        self,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> SyntaxTree:
        """Persistently insert elements before a non-root target."""
        self._check_target(target)
        if not target.path:
            raise ValueError("cannot insert beside the syntax tree root")
        green = element.green if isinstance(element, SyntaxElement) else element
        additions: list[GreenElement] = [green]
        if separator:
            additions.append(GreenTrivia("raw", separator))
        return self._with_root(
            _insert_at(self.green_root, target.path, additions, before=True)
        )

    def insert_after(
        self,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> SyntaxTree:
        """Persistently insert elements after a non-root target."""
        self._check_target(target)
        if not target.path:
            raise ValueError("cannot insert beside the syntax tree root")
        green = element.green if isinstance(element, SyntaxElement) else element
        additions: list[GreenElement] = []
        if separator:
            additions.append(GreenTrivia("raw", separator))
        additions.append(green)
        return self._with_root(
            _insert_at(self.green_root, target.path, additions, before=False)
        )

    def _check_target(self, target: SyntaxElement) -> None:
        if target.tree is not self:
            raise ValueError("target belongs to a different immutable syntax snapshot")

    def _with_root(self, root: GreenNode) -> SyntaxTree:
        return SyntaxTree(
            language=self.language,
            green_root=root,
            diagnostics=(),
            source_name=self.source_name,
        )


def _replace_at(
    root: GreenNode,
    path: tuple[int, ...],
    element: GreenElement,
) -> GreenNode:
    index = path[0]
    if len(path) == 1:
        return root.replacing_child(index, element)
    child = root.children[index].element
    if not isinstance(child, GreenNode):
        raise ValueError("rewrite path crosses a non-node")
    return root.replacing_child(index, _replace_at(child, path[1:], element))


def _remove_at(root: GreenNode, path: tuple[int, ...]) -> GreenNode:
    index = path[0]
    if len(path) == 1:
        return root.removing_child(index)
    child = root.children[index].element
    if not isinstance(child, GreenNode):
        raise ValueError("rewrite path crosses a non-node")
    return root.replacing_child(index, _remove_at(child, path[1:]))


def _insert_at(
    root: GreenNode,
    path: tuple[int, ...],
    additions: Iterable[GreenElement],
    *,
    before: bool,
) -> GreenNode:
    index = path[0]
    if len(path) == 1:
        children = list(root.children)
        insert_index = index if before else index + 1
        for element in reversed(list(additions)):
            children.insert(insert_index, GreenChild(element))
        return GreenNode(
            root.kind,
            tuple(children),
            root.named,
            root.missing,
            root.error,
        )
    child = root.children[index].element
    if not isinstance(child, GreenNode):
        raise ValueError("rewrite path crosses a non-node")
    return root.replacing_child(
        index,
        _insert_at(child, path[1:], additions, before=before),
    )
