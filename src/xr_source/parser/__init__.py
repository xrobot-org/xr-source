"""Parser backend adapters. Tree-sitter is currently the only concrete backend."""

from .tree_sitter import TreeSitterSyntaxParser

__all__ = ["TreeSitterSyntaxParser"]
