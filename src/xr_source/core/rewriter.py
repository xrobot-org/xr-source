"""Persistent syntax-tree rewriter that preserves unchanged green subtrees."""

from __future__ import annotations

from .green import GreenChild, GreenElement, GreenNode, GreenToken, GreenTrivia
from .tree import SyntaxTree


class SyntaxRewriter:
    """Functional green-tree rewriter.

    Subclass visit_node/visit_token/visit_trivia. Returning the original object
    keeps identity and allows unchanged ancestor branches to be reused.
    """
    def rewrite(self, tree: SyntaxTree) -> SyntaxTree:
        """Rewrite a tree and return a new snapshot with the same language/source metadata."""
        root = self.visit_node(tree.green_root)
        return SyntaxTree(tree.language, root, tree.diagnostics, tree.source_name)

    def visit_node(self, node: GreenNode) -> GreenNode:
        """Rewrite children recursively and rebuild this node only if some child changed."""
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
        """Handle one syntax token."""
        return token

    def visit_trivia(self, trivia: GreenTrivia) -> GreenElement:
        """Handle one preserved trivia element."""
        return trivia

    def visit(self, element: GreenElement) -> GreenElement:
        """Dispatch this element to the appropriate visitor or rewriter hook."""
        if isinstance(element, GreenNode):
            return self.visit_node(element)
        if isinstance(element, GreenToken):
            return self.visit_token(element)
        return self.visit_trivia(element)
