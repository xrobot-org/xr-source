"""Language-neutral document facade for querying and safely editing syntax trees."""

from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar

from .diagnostic import Diagnostic
from .grammar import GrammarNodeSpec, LanguageGrammar
from .green import GreenElement
from .red import SyntaxElement, SyntaxNode, SyntaxToken
from .tree import SyntaxTree

# ---------------------------------------------------------------------------
# Language-neutral document facade
# ---------------------------------------------------------------------------

class SyntaxParserProtocol(Protocol):
    """Minimal parser contract required by SyntaxDocument."""
    def parse(
        self,
        source: str | bytes,
        *,
        source_name: str | None = None,
    ) -> SyntaxTree:
        """Parse text or bytes into one immutable syntax-tree snapshot."""
        ...


DocumentT = TypeVar("DocumentT", bound="SyntaxDocument")


class SyntaxDocument:
    """Language-neutral immutable document facade over one SyntaxTree snapshot.

    Low-level SyntaxTree edits preserve green sharing. High-level document edits
    render and reparse the changed bytes so parser-owned field labels, diagnostics
    and language invariants cannot become stale.
    """
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
        """Return the red root view for this document snapshot."""
        return self.tree.root

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Return parser diagnostics captured for this immutable snapshot."""
        return self.tree.diagnostics

    def render(self) -> str:
        """Render represented source text without applying formatting rules."""
        return self.tree.render()

    def render_bytes(self) -> bytes:
        """Render represented source bytes while preserving surrogate-escaped input."""
        return self.tree.render_bytes()

    def grammar_spec(self, element: SyntaxElement) -> GrammarNodeSpec | None:
        """Map a parsed node/token back to its versioned grammar contract when available."""
        grammar = self.grammar
        if grammar is None or not isinstance(element, (SyntaxNode, SyntaxToken)):
            return None
        return grammar.node(element.kind, named=element.named)

    # High-level edits deliberately return a fresh reparsed snapshot. The
    # low-level tree API can preserve green sharing, but document consumers must
    # never observe stale parser field labels or diagnostics after an edit.
    def replace(
        self: DocumentT,
        target: SyntaxElement,
        replacement: SyntaxElement | GreenElement,
    ) -> DocumentT:
        """Replace one element and return a new reparsed document snapshot."""
        return self._reparse(self.tree.replace(target, replacement).render_bytes())

    def remove(self: DocumentT, target: SyntaxElement) -> DocumentT:
        """Remove one element and return a new reparsed document snapshot."""
        return self._reparse(self.tree.remove(target).render_bytes())

    def insert_before(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        """Insert an element before a target and return a new reparsed document snapshot."""
        changed = self.tree.insert_before(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def insert_after(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        """Insert an element after a target and return a new reparsed document snapshot."""
        changed = self.tree.insert_after(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def elements(self, kind: str) -> tuple[SyntaxElement, ...]:
        """Return all matching syntax elements, including named tokens as well as nodes."""
        return tuple(self.root.descendants(kind, include_self=True))

    def nodes(self, kind: str) -> tuple[SyntaxNode, ...]:
        """Return only matching SyntaxNode objects."""
        return tuple(
            element
            for element in self.elements(kind)
            if isinstance(element, SyntaxNode)
        )

    def _reparse(self: DocumentT, source: bytes) -> DocumentT:
        # Reparse at the language-document boundary so field labels, diagnostics
        # and error-recovery structure always come from the parser that owns them.
        # Incremental parsing can optimize this later without changing the API.
        tree = self._parser.parse(source, source_name=self.tree.source_name)
        return type(self)(tree, self._parser)
