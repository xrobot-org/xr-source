"""集中导出 C++ 原生解析器、grammar、查询视图、片段工厂和构建器。
C++ frontend: parser, grammar metadata, structured queries, views, and builders.
"""

from .builder import CppBlockBuilder, CppFileBuilder, CppFunctionBuilder
from .document import CppDocument, CppRegion
from .factory import CppFactory
from .grammar import CPP_GRAMMAR, GRAMMAR_REVISION, GRAMMAR_VERSION
from .invocation import (
    CppIdentifierOccurrence,
    CppInvocationView,
    identifier_occurrences,
    split_source_list,
)
from .lexical import CppLexicalToken, code_tokens, matching_delimiter
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
    "CppIdentifierOccurrence",
    "CppIncludeView",
    "CppLexicalToken",
    "CppInvocationView",
    "CppParameterView",
    "code_tokens",
    "CppParser",
    "CppTemplateParameterView",
    "CppVariableView",
    "matching_delimiter",
    "identifier_occurrences",
    "split_source_list",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
    "CppRegion",
]
