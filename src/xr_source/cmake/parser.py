from __future__ import annotations

from tree_sitter import Language

from xr_source.parser import TreeSitterSyntaxParser

from .grammar import CMAKE_GRAMMAR


def _cmake_language() -> Language:
    try:
        from tree_sitter_language_pack import get_language
    except ImportError as error:
        raise RuntimeError(
            "CMake support requires the optional 'xr-source[cmake]' dependency"
        ) from error
    return get_language("cmake")


class CMakeParser(TreeSitterSyntaxParser):
    grammar = CMAKE_GRAMMAR

    def __init__(self) -> None:
        super().__init__("cmake", _cmake_language())
