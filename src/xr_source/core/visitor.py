from __future__ import annotations

from .red import SyntaxElement, SyntaxNode, SyntaxToken, SyntaxTrivia


class SyntaxVisitor:
    def visit(self, element: SyntaxElement) -> None:
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
        return True

    def leave_node(self, node: SyntaxNode) -> None:
        pass

    def visit_token(self, token: SyntaxToken) -> None:
        pass

    def visit_trivia(self, trivia: SyntaxTrivia) -> None:
        pass
