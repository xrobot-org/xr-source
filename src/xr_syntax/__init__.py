"""定义 xr-syntax 顶层公共接口，集中导出语言无关语法核心以及 C++ 前端的常用类型。
Public package surface for the language-neutral source model and C++ frontend.
"""

from .core import (
    Diagnostic,
    GreenChild,
    GreenNode,
    GreenToken,
    GreenTrivia,
    ParserKindInfo,
    ParserSchema,
    SourcePoint,
    SourceSpan,
    SyntaxElement,
    SyntaxFragment,
    SyntaxNode,
    SyntaxToken,
    SyntaxTree,
    SyntaxTrivia,
)
from .cpp import (
    CppBlockBuilder,
    CppDocument,
    CppFactory,
    CppFileBuilder,
    CppFunctionBuilder,
    CppParser,
    CppRegion,
)

# ---------------------------------------------------------------------------
# 模块实现：定义 xr-syntax 顶层公共接口，集中导出语言无关语法核心以及 C++ 前端的常用类型。
# ---------------------------------------------------------------------------

__all__ = [
    "CppBlockBuilder",
    "CppDocument",
    "CppFactory",
    "CppFileBuilder",
    "CppFunctionBuilder",
    "CppParser",
    "CppRegion",
    "Diagnostic",
    "GreenChild",
    "GreenNode",
    "GreenToken",
    "GreenTrivia",
    "ParserKindInfo",
    "ParserSchema",
    "SourcePoint",
    "SourceSpan",
    "SyntaxElement",
    "SyntaxFragment",
    "SyntaxNode",
    "SyntaxToken",
    "SyntaxTree",
    "SyntaxTrivia",
]
