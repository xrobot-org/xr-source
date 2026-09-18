from __future__ import annotations

import tree_sitter_cpp
from tree_sitter import Language

from xr_source.parser import TreeSitterSyntaxParser

from .grammar import CPP_GRAMMAR


class CppParser(TreeSitterSyntaxParser):
    grammar = CPP_GRAMMAR

    def __init__(self) -> None:
        super().__init__("cpp", Language(tree_sitter_cpp.language()))
