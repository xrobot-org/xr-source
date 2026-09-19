"""集中导出不可变语法树、grammar、源码范围、文档和 parser schema 等核心抽象。
Core immutable syntax, grammar, span, document, and parser-schema abstractions.
"""

from .diagnostic import Diagnostic
from .document import SyntaxDocument, SyntaxParserProtocol
from .grammar import (
    GrammarNodeSpec,
    GrammarSlot,
    GrammarTypeRef,
    LanguageGrammar,
)
from .fragment import SyntaxFragment
from .green import GreenChild, GreenElement, GreenNode, GreenToken, GreenTrivia
from .parser_schema import ParserKindInfo, ParserSchema
from .red import SyntaxElement, SyntaxNode, SyntaxToken, SyntaxTrivia
from .span import SourcePoint, SourceSpan
from .text import decode_source, encode_source
from .tree import SyntaxTree

__all__ = [
    "Diagnostic",
    "decode_source",
    "encode_source",
    "GreenChild",
    "GreenElement",
    "GreenNode",
    "GreenToken",
    "GreenTrivia",
    "GrammarNodeSpec",
    "GrammarSlot",
    "GrammarTypeRef",
    "LanguageGrammar",
    "ParserKindInfo",
    "ParserSchema",
    "SourcePoint",
    "SourceSpan",
    "SyntaxDocument",
    "SyntaxFragment",
    "SyntaxElement",
    "SyntaxNode",
    "SyntaxParserProtocol",
    "SyntaxToken",
    "SyntaxTree",
    "SyntaxTrivia",
]
