"""CMake parser configuration sourced from the optional language-pack grammar."""

from __future__ import annotations

try:
    from tree_sitter import Language
except ImportError as error:  # pragma: no cover - 仅在未安装 cmake extra 时触发
    raise RuntimeError(
        "CMake support requires the optional 'xr-source[cmake]' dependency"
    ) from error

from xr_source.parser.tree_sitter import TreeSitterSyntaxParser

from .grammar import CMAKE_GRAMMAR


def _cmake_language() -> Language:
    """从 optional language-pack 获取 CMake grammar。"""
    try:
        from tree_sitter_language_pack import get_language
    except ImportError as error:
        raise RuntimeError(
            "CMake support requires the optional 'xr-source[cmake]' dependency"
        ) from error
    return get_language("cmake")


class CMakeParser(TreeSitterSyntaxParser):
    """CMake 仍采用 optional Tree-sitter backend；C++ frontend 与此无关。"""

    grammar = CMAKE_GRAMMAR

    def __init__(self) -> None:
        """构造 CMake parser adapter。"""
        super().__init__("cmake", _cmake_language())
