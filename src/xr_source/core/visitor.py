"""定义面向 red 语法视图的只读深度优先访问器。"""

from __future__ import annotations

from .red import SyntaxElement, SyntaxNode, SyntaxToken, SyntaxTrivia


class SyntaxVisitor:
    """按源码顺序深度优先遍历 red 语法元素的只读访问器。"""
    def visit(self, element: SyntaxElement) -> None:
        """按源码顺序分派 node、token 和 trivia，并递归遍历 node children。"""
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
        """在进入一个 SyntaxNode 时调用；默认不做额外处理。"""
        return True

    def leave_node(self, node: SyntaxNode) -> None:
        """在一个 SyntaxNode 的 children 遍历结束后调用。"""
        pass

    def visit_token(self, token: SyntaxToken) -> None:
        """访问一个 SyntaxToken；默认不做额外处理。"""
        pass

    def visit_trivia(self, trivia: SyntaxTrivia) -> None:
        """访问一个 SyntaxTrivia；默认不做额外处理。"""
        pass
