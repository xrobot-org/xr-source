"""C++ parser configuration backed by the validated Tree-sitter C++ grammar."""

from __future__ import annotations

import tree_sitter_cpp
from tree_sitter import Language

from xr_source.parser import TreeSitterSyntaxParser

from .grammar import CPP_GRAMMAR


class CppParser(TreeSitterSyntaxParser):
    """Validated default C++ parser backend paired with the packaged C++ grammar contract."""
    grammar = CPP_GRAMMAR

    def __init__(self) -> None:
        super().__init__("cpp", Language(tree_sitter_cpp.language()))
