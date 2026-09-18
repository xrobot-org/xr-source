"""集中导出 C++ 原生解析器、grammar、查询视图、片段工厂和构建器。"""

from .builder import CppBlockBuilder, CppFileBuilder, CppFunctionBuilder
from .document import CppDocument, CppRegion
from .factory import CppFactory
from .grammar import CPP_GRAMMAR, GRAMMAR_REVISION, GRAMMAR_VERSION
from .parser import CppParser
from .view import (
    CppCallView,
    CppClassView,
    CppFunctionView,
    CppIncludeView,
    CppParameterView,
    CppTemplateParameterView,
    CppVariableView,
)

__all__ = [
    "CPP_GRAMMAR",
    "CppBlockBuilder",
    "CppCallView",
    "CppClassView",
    "CppDocument",
    "CppFactory",
    "CppFileBuilder",
    "CppFunctionBuilder",
    "CppFunctionView",
    "CppIncludeView",
    "CppParameterView",
    "CppParser",
    "CppTemplateParameterView",
    "CppVariableView",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
    "CppRegion",
]
