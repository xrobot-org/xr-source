from __future__ import annotations

from .green import GreenChild, GreenElement, GreenNode, GreenToken, GreenTrivia
from .tree import SyntaxTree


class SyntaxRewriter:
    def rewrite(self, tree: SyntaxTree) -> SyntaxTree:
        root = self.visit_node(tree.green_root)
        return SyntaxTree(tree.language, root, tree.diagnostics, tree.source_name)

    def visit_node(self, node: GreenNode) -> GreenNode:
        changed = False
        children: list[GreenChild] = []
        for child in node.children:
            element = self.visit(child.element)
            changed |= element is not child.element
            children.append(GreenChild(element, child.field))
        if not changed:
            return node
        return GreenNode(
            node.kind,
            tuple(children),
            node.named,
            node.missing,
            node.error,
        )

    def visit_token(self, token: GreenToken) -> GreenElement:
        return token

    def visit_trivia(self, trivia: GreenTrivia) -> GreenElement:
        return trivia

    def visit(self, element: GreenElement) -> GreenElement:
        if isinstance(element, GreenNode):
            return self.visit_node(element)
        if isinstance(element, GreenToken):
            return self.visit_token(element)
        return self.visit_trivia(element)
