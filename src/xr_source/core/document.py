from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar

from .diagnostic import Diagnostic
from .grammar import GrammarNodeSpec, LanguageGrammar
from .green import GreenElement
from .red import SyntaxElement, SyntaxNode, SyntaxToken
from .tree import SyntaxTree


class SyntaxParserProtocol(Protocol):
    def parse(
        self,
        source: str | bytes,
        *,
        source_name: str | None = None,
    ) -> SyntaxTree: ...


DocumentT = TypeVar("DocumentT", bound="SyntaxDocument")


class SyntaxDocument:
    __slots__ = ("tree", "_parser")

    language: str
    grammar: ClassVar[LanguageGrammar | None] = None

    def __init__(
        self,
        tree: SyntaxTree,
        parser: SyntaxParserProtocol,
    ) -> None:
        if tree.language != self.language:
            raise ValueError(
                f"expected {self.language!r} syntax tree, got {tree.language!r}"
            )
        self.tree = tree
        self._parser = parser

    @property
    def root(self) -> SyntaxNode:
        return self.tree.root

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.tree.diagnostics

    def render(self) -> str:
        return self.tree.render()

    def render_bytes(self) -> bytes:
        return self.tree.render_bytes()

    def grammar_spec(self, element: SyntaxElement) -> GrammarNodeSpec | None:
        grammar = self.grammar
        if grammar is None or not isinstance(element, (SyntaxNode, SyntaxToken)):
            return None
        return grammar.node(element.kind, named=element.named)

    def replace(
        self: DocumentT,
        target: SyntaxElement,
        replacement: SyntaxElement | GreenElement,
    ) -> DocumentT:
        return self._reparse(self.tree.replace(target, replacement).render_bytes())

    def remove(self: DocumentT, target: SyntaxElement) -> DocumentT:
        return self._reparse(self.tree.remove(target).render_bytes())

    def insert_before(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        changed = self.tree.insert_before(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def insert_after(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        changed = self.tree.insert_after(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def elements(self, kind: str) -> tuple[SyntaxElement, ...]:
        return tuple(self.root.descendants(kind, include_self=True))

    def nodes(self, kind: str) -> tuple[SyntaxNode, ...]:
        return tuple(
            element
            for element in self.elements(kind)
            if isinstance(element, SyntaxNode)
        )

    def _reparse(self: DocumentT, source: bytes) -> DocumentT:
        tree = self._parser.parse(source, source_name=self.tree.source_name)
        return type(self)(tree, self._parser)
