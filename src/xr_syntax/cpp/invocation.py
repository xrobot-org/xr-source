"""提供宏式 NAME(...) invocation 的词法查询和逗号列表切分。
Lexical queries for macro-like NAME(...) invocations and comma-delimited source lists.
"""

from __future__ import annotations

from dataclasses import dataclass

from xr_syntax.core import SourceSpan, SyntaxTree, decode_source

from .lexer import _Lexeme, _Lexer


@dataclass(frozen=True)
class CppInvocationView:
    """表示指定名字的词法 invocation 及其精确源码实参。
    Lexical view of one named invocation together with exact source arguments.
    """

    tree: SyntaxTree
    name: str
    span: SourceSpan
    arguments: tuple[str, ...]

    @property
    def text(self) -> str:
        """返回 invocation 的精确源码文本。
        Return exact source text for the invocation.
        """
        return decode_source(self.tree.render_bytes()[self.span.start : self.span.end])

    @property
    def line(self) -> int:
        """返回一基源码行号。
        Return the one-based source line number.
        """
        return self.tree.render_bytes()[: self.span.start].count(b"\n") + 1


def split_source_list(source: str, *, template_angles: bool = False) -> tuple[str, ...]:
    """按顶层逗号切分源码列表，并按需把模板角括号视为嵌套。
    Split source on top-level commas, optionally treating template angles as nesting.
    """
    lexemes, _ = _Lexer(source).scan()
    significant = [item for item in lexemes if not item.trivia and item.kind != "comment"]
    if not significant:
        return ()
    separators = _top_level_commas(significant, template_angles=template_angles)
    encoded = source.encode("utf-8", errors="surrogateescape")
    result = []
    start = 0
    for item in separators:
        text = decode_source(encoded[start:item.start]).strip()
        if not text:
            raise ValueError("empty argument in C++ source list")
        result.append(text)
        start = item.end
    text = decode_source(encoded[start:]).strip()
    if not text:
        raise ValueError("empty argument in C++ source list")
    result.append(text)
    return tuple(result)


def find_invocations(
    tree: SyntaxTree,
    name: str,
    *,
    template_angles: bool = False,
) -> tuple[CppInvocationView, ...]:
    """在语法快照中查找指定 NAME(...) invocation。
    Find lexical NAME(...) invocations in one syntax-tree snapshot.
    """
    text = tree.render()
    lexemes, _ = _Lexer(text).scan()
    significant = [
        (index, item)
        for index, item in enumerate(lexemes)
        if not item.trivia and item.kind != "comment"
    ]
    positions = {index: position for position, (index, _) in enumerate(significant)}
    encoded = tree.render_bytes()
    result = []
    for index, item in significant:
        if item.kind != "identifier" or item.text != name:
            continue
        if _inside_preprocessor(lexemes, index):
            continue
        position = positions[index]
        if position + 1 >= len(significant):
            continue
        open_index, opening = significant[position + 1]
        if opening.text != "(":
            continue
        close_index = _matching_paren(lexemes, open_index)
        if close_index is None:
            continue
        closing = lexemes[close_index]
        inner = decode_source(encoded[opening.end : closing.start])
        arguments = (
            split_source_list(inner, template_angles=template_angles)
            if inner.strip()
            else ()
        )
        result.append(
            CppInvocationView(
                tree,
                name,
                SourceSpan(item.start, closing.end),
                arguments,
            )
        )
    return tuple(result)


def _matching_paren(lexemes: list[_Lexeme], opening: int) -> int | None:
    """匹配词法 invocation 的外层圆括号。
    Match the outer parenthesis of a lexical invocation.
    """
    depth = 0
    for index in range(opening, len(lexemes)):
        item = lexemes[index]
        if item.trivia or item.kind == "comment":
            continue
        if item.text == "(":
            depth += 1
        elif item.text == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _inside_preprocessor(lexemes: list[_Lexeme], index: int) -> bool:
    """判断 lexeme 是否位于预处理逻辑行。
    Return whether a lexeme belongs to a preprocessor logical line.
    """
    cursor = index - 1
    while cursor >= 0:
        item = lexemes[cursor]
        if item.trivia and ("\n" in item.text or "\r" in item.text):
            break
        if not item.trivia and item.kind != "comment" and item.text == "#":
            return True
        cursor -= 1
    return False


def _top_level_commas(
    items: list[_Lexeme],
    *,
    template_angles: bool,
) -> list[_Lexeme]:
    """返回不处于括号或模板角括号内的逗号 lexeme。
    Return commas outside delimiter nesting and optional template-angle nesting.
    """
    result = []
    round_depth = square_depth = brace_depth = angle_depth = 0
    for item in items:
        text = item.text
        if text == "(":
            round_depth += 1
        elif text == ")":
            round_depth = max(0, round_depth - 1)
        elif text == "[":
            square_depth += 1
        elif text == "]":
            square_depth = max(0, square_depth - 1)
        elif text == "{":
            brace_depth += 1
        elif text == "}":
            brace_depth = max(0, brace_depth - 1)
        elif template_angles and text == "<":
            angle_depth += 1
        elif template_angles and text == ">" and angle_depth:
            angle_depth -= 1
        elif template_angles and text == ">>" and angle_depth:
            angle_depth = max(0, angle_depth - 2)
        elif text == "," and not (round_depth or square_depth or brace_depth or angle_depth):
            result.append(item)
    return result
