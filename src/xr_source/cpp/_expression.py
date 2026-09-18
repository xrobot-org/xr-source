"""C++ parser 内部的语句与表达式结构解析。"""

from __future__ import annotations

from xr_source.core import GreenElement, GreenNode, GreenToken

from ._ranges import _deduplicate_replacements, _Replacement
from .lexer import _LITERAL_KINDS


class _ExpressionMixin:
    """解析 compound statement、控制流、调用和常见表达式结构。"""

    def _parse_compound(self, open_brace: int, close_brace: int) -> GreenNode:
        """解析函数/控制流复合语句，并递归结构化内部声明与调用。"""
        replacements = self._parse_scope(
            open_brace + 1,
            close_brace,
            context="block",
        )
        return self._compose(
            "compound_statement",
            open_brace,
            close_brace + 1,
            replacements,
        )

    def _parse_return(self, start: int, end: int) -> _Replacement:
        """解析 return 语句及返回表达式。"""
        significant = self._significant(start, end)
        semicolon = (
            significant[-1]
            if significant and self.lexemes[significant[-1]].text == ";"
            else end
        )
        expression_start = (
            self._next_significant(significant[0] + 1, semicolon)
            if significant
            else None
        )
        replacements: list[_Replacement] = []
        if expression_start is not None:
            expression = self._parse_expression(expression_start, semicolon)
            replacements.append(
                _Replacement(expression_start, semicolon, expression)
            )
        node = self._compose("return_statement", start, end, replacements)
        return _Replacement(start, end, node)

    def _parse_control(
        self,
        start: int,
        end: int,
        keyword: str,
    ) -> _Replacement:
        """解析 if/for/while/switch/catch 的条件和复合 body。"""
        significant = self._significant(start, end)
        open_paren = next(
            (
                index
                for index in significant[1:]
                if self.lexemes[index].text == "("
            ),
            None,
        )
        replacements: list[_Replacement] = []
        cursor = start + 1
        if open_paren is not None and open_paren in self._pairs:
            close_paren = self._pairs[open_paren]
            if close_paren < end:
                condition_start = self._next_significant(
                    open_paren + 1,
                    close_paren,
                )
                if condition_start is not None:
                    condition = self._parse_expression(
                        condition_start,
                        close_paren,
                    )
                    replacements.append(
                        _Replacement(
                            condition_start,
                            close_paren,
                            condition,
                            "condition",
                        )
                    )
                cursor = close_paren + 1

        body_open = self._next_significant(cursor, end)
        if (
            body_open is not None
            and self.lexemes[body_open].text == "{"
            and body_open in self._pairs
        ):
            body_close = self._pairs[body_open]
            if body_close < end:
                body = self._parse_compound(body_open, body_close)
                replacements.append(
                    _Replacement(
                        body_open,
                        body_close + 1,
                        body,
                        "consequence",
                    )
                )

        kind = {
            "if": "if_statement",
            "for": "for_statement",
            "while": "while_statement",
            "switch": "switch_statement",
            "catch": "catch_clause",
        }[keyword]
        node = self._compose(kind, start, end, replacements)
        return _Replacement(start, end, node)

    def _parse_do(self, start: int, end: int) -> _Replacement:
        """解析 do/while 结构；body 内部仍递归解析。"""
        replacements: list[_Replacement] = []
        body_open = self._next_significant(start + 1, end)
        if (
            body_open is not None
            and self.lexemes[body_open].text == "{"
            and body_open in self._pairs
        ):
            body_close = self._pairs[body_open]
            body = self._parse_compound(body_open, body_close)
            replacements.append(
                _Replacement(
                    body_open,
                    body_close + 1,
                    body,
                    "body",
                )
            )
        node = self._compose("do_statement", start, end, replacements)
        return _Replacement(start, end, node)

    def _parse_concept(self, start: int, end: int) -> _Replacement:
        """解析 concept 定义，并继续解析等号后的表达式。"""
        equal = self._find_top_level_token(start, end, "=")
        replacements: list[_Replacement] = []
        if equal is not None:
            value_end = self._before_trailing_semicolon(start, end)
            value_start = self._next_significant(equal + 1, value_end)
            if value_start is not None:
                expression = self._parse_expression(value_start, value_end)
                replacements.append(
                    _Replacement(
                        value_start,
                        value_end,
                        expression,
                        "value",
                    )
                )
        node = self._compose("concept_definition", start, end, replacements)
        return _Replacement(start, end, node)

    def _parse_expression(self, start: int, end: int) -> GreenElement:
        """解析常见表达式；不能细分时保留为 source_expression。"""
        trimmed = self._trim(start, end)
        if trimmed is None:
            return GreenNode("source_expression", (), named=True)

        start, end = trimmed
        significant = self._significant(start, end)
        if not significant:
            return self._compose("source_expression", start, end, [])

        first = significant[0]
        first_text = self.lexemes[first].text

        if first_text == "[" and first in self._pairs:
            body_open = next(
                (
                    index
                    for index in significant
                    if self.lexemes[index].text == "{"
                    and index in self._pairs
                ),
                None,
            )
            if body_open is not None and self._pairs[body_open] < end:
                body_close = self._pairs[body_open]
                body = self._parse_compound(body_open, body_close)
                return self._compose(
                    "lambda_expression",
                    start,
                    end,
                    [
                        _Replacement(
                            body_open,
                            body_close + 1,
                            body,
                            "body",
                        )
                    ],
                )

        if first_text == "requires":
            body_open = next(
                (
                    index
                    for index in significant
                    if self.lexemes[index].text == "{"
                    and index in self._pairs
                ),
                None,
            )
            replacements: list[_Replacement] = []
            if body_open is not None and self._pairs[body_open] < end:
                body_close = self._pairs[body_open]
                body = self._parse_compound(body_open, body_close)
                replacements.append(
                    _Replacement(
                        body_open,
                        body_close + 1,
                        body,
                        "body",
                    )
                )
            return self._compose(
                "requires_expression",
                start,
                end,
                replacements,
            )

        if first_text == "co_await":
            return self._compose("co_await_expression", start, end, [])
        if first_text == "new":
            return self._compose("new_expression", start, end, [])
        if first_text == "delete":
            return self._compose("delete_expression", start, end, [])

        if self.lexemes[first].text == "(" and first in self._pairs:
            close = self._pairs[first]
            if close == significant[-1]:
                if any(
                    self.lexemes[index].text == "..."
                    for index in significant
                ):
                    return self._compose(
                        "fold_expression",
                        start,
                        end,
                        [],
                    )
                inner_start = self._next_significant(first + 1, close)
                replacements = []
                if inner_start is not None:
                    inner = self._parse_expression(inner_start, close)
                    replacements.append(
                        _Replacement(inner_start, close, inner)
                    )
                return self._compose(
                    "parenthesized_expression",
                    start,
                    end,
                    replacements,
                )

        operator = self._lowest_precedence_operator(start, end)
        if operator is not None:
            left_range = self._trim(start, operator)
            right_range = self._trim(operator + 1, end)
            if left_range is not None and right_range is not None:
                left = self._parse_expression(*left_range)
                right = self._parse_expression(*right_range)
                operator_text = self.lexemes[operator].text
                operator_token = GreenToken(operator_text, operator_text)
                assignment = (
                    operator_text.endswith("=")
                    and operator_text not in {"==", "!=", "<=", ">="}
                )
                kind = (
                    "assignment_expression"
                    if assignment
                    else "binary_expression"
                )
                return self._compose(
                    kind,
                    start,
                    end,
                    [
                        _Replacement(
                            left_range[0],
                            left_range[1],
                            left,
                            "left",
                        ),
                        _Replacement(
                            operator,
                            operator + 1,
                            operator_token,
                            "operator",
                        ),
                        _Replacement(
                            right_range[0],
                            right_range[1],
                            right,
                            "right",
                        ),
                    ],
                )

        call = self._find_call_suffix(start, end)
        if call is not None:
            open_paren, close_paren = call
            callee_range = self._trim(start, open_paren)
            if callee_range is not None:
                callee = self._parse_callee(*callee_range)
                arguments = self._parse_argument_list(
                    open_paren,
                    close_paren,
                )
                return self._compose(
                    "call_expression",
                    start,
                    end,
                    [
                        _Replacement(
                            callee_range[0],
                            callee_range[1],
                            callee,
                            "function",
                        ),
                        _Replacement(
                            open_paren,
                            close_paren + 1,
                            arguments,
                            "arguments",
                        ),
                    ],
                )

        if len(significant) == 1:
            token = self.lexemes[significant[0]]
            if token.kind == "identifier":
                return GreenToken(
                    "identifier",
                    token.text,
                    named=True,
                )
            if token.kind in _LITERAL_KINDS:
                return token.green()

        nested = self._scan_nested_calls(start, end)
        return self._compose(
            "source_expression",
            start,
            end,
            nested,
        )

    def _parse_callee(self, start: int, end: int) -> GreenElement:
        """给调用目标建立轻量结构；不做名称解析。"""
        text = self._text(start, end)
        significant = self._significant(start, end)
        if (
            len(significant) == 1
            and self.lexemes[significant[0]].kind == "identifier"
        ):
            return GreenToken("identifier", text, named=True)
        if "::" in (
            self.lexemes[index].text
            for index in significant
        ):
            return self._compose(
                "qualified_identifier",
                start,
                end,
                [],
            )
        if any(
            self.lexemes[index].text in {".", "->"}
            for index in significant
        ):
            return self._compose(
                "field_expression",
                start,
                end,
                [],
            )
        return self._compose(
            "source_expression",
            start,
            end,
            [],
        )

    def _parse_argument_list(
        self,
        open_paren: int,
        close_paren: int,
    ) -> GreenNode:
        """解析调用实参列表，使每个实参都可单独查询/重写。"""
        replacements: list[_Replacement] = []
        parts = self._split_top_level(
            open_paren + 1,
            close_paren,
            ",",
        )
        for part_start, part_end in parts:
            trimmed = self._trim(part_start, part_end)
            if trimmed is None:
                continue
            argument = self._parse_expression(*trimmed)
            replacements.append(
                _Replacement(
                    trimmed[0],
                    trimmed[1],
                    argument,
                )
            )
        return self._compose(
            "argument_list",
            open_paren,
            close_paren + 1,
            replacements,
        )

    def _scan_nested_calls(
        self,
        start: int,
        end: int,
    ) -> list[_Replacement]:
        """在未完整分类的表达式中保守识别不重叠的调用。"""
        result: list[_Replacement] = []
        significant = self._significant(start, end)
        for position, index in enumerate(significant):
            if (
                self.lexemes[index].text != "("
                or index not in self._pairs
            ):
                continue
            close = self._pairs[index]
            if close >= end or position == 0:
                continue

            previous = significant[position - 1]
            previous_text = self.lexemes[previous].text
            if (
                self.lexemes[previous].kind != "identifier"
                and previous_text not in {">", ")", "]"}
            ):
                continue

            callee_start = previous
            while True:
                before = self._previous_significant(
                    callee_start - 1,
                    start,
                )
                if (
                    before is None
                    or self.lexemes[before].text not in {"::", ".", "->"}
                ):
                    break
                owner = self._previous_significant(
                    before - 1,
                    start,
                )
                if owner is None:
                    break
                callee_start = owner

            node = self._parse_expression(
                callee_start,
                close + 1,
            )
            result.append(
                _Replacement(
                    callee_start,
                    close + 1,
                    node,
                )
            )
        return _deduplicate_replacements(result)
