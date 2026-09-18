"""Read-only visitor hooks for walking red syntax views."""

from __future__ import annotations

from .red import SyntaxElement, SyntaxNode, SyntaxToken, SyntaxTrivia


class SyntaxVisitor:
    """Read-only depth-first visitor over red syntax views."""
    def visit(self, element: SyntaxElement) -> None:
        """Dispatch to node/token/trivia hooks while preserving source traversal order."""
        if isinstance(element, SyntaxNode):
            if self.visit_node(element):
                for child in element.children:
                    self.visit(child)
            self.leave_node(element)
        elif isinstance(element, SyntaxToken):
            self.visit_token(element)
        elif isinstance(element, SyntaxTrivia):
            self.visit_trivia(element)
        else:
            raise TypeError(type(element))

    def visit_node(self, node: SyntaxNode) -> bool:
        """Handle one syntax node."""
        return True

    def leave_node(self, node: SyntaxNode) -> None:
        """Handle completion of a syntax-node traversal."""
        pass

    def visit_token(self, token: SyntaxToken) -> None:
        """Handle one syntax token."""
        pass

    def visit_trivia(self, trivia: SyntaxTrivia) -> None:
        """Handle one preserved trivia element."""
        pass
