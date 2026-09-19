"""配置可选的 CMake 解析后端；Tree-sitter 仅在 CMake extra 中使用，与 C++ 前端无关。

CMake parser configuration sourced from the optional language-pack grammar.
"""

from __future__ import annotations

try:
    from tree_sitter import Language
except ImportError as error:  # pragma: no cover - CMake extra 未安装 / EN: CMake extra unavailable
    raise RuntimeError(
        "CMake support requires the optional 'xr-source[cmake]' dependency"
    ) from error

from xr_source.parser.tree_sitter import TreeSitterSyntaxParser

from .grammar import CMAKE_GRAMMAR


def _cmake_language() -> Language:
    """从 optional language-pack 获取 CMake grammar。

    Load the CMake grammar from the optional language pack.
    """
    try:
        from tree_sitter_language_pack import get_language
    except ImportError as error:
        raise RuntimeError(
            "CMake support requires the optional 'xr-source[cmake]' dependency"
        ) from error
    return get_language("cmake")


class CMakeParser(TreeSitterSyntaxParser):
    """CMake 仍采用 optional Tree-sitter backend；C++ frontend 与此无关。

    CMake parser backed by the optional Tree-sitter adapter; it is independent of the C++
    frontend.
    """

    grammar = CMAKE_GRAMMAR

    def __init__(self) -> None:
        """构造 CMake parser adapter。

        Construct the optional Tree-sitter-backed CMake parser adapter.
        """
        super().__init__("cmake", _cmake_language())
