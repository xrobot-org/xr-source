"""C++ parser 内部的函数/变量 declarator 识别辅助。"""

from __future__ import annotations

from xr_source.core import GreenChild, GreenElement, GreenNode, GreenToken

from ._ranges import _Replacement
from .lexer import _CONTROL, _LITERAL_KINDS, _QUALIFIERS, _STORAGE, _TYPE_WORDS
from ._support import _ParserSupport


class _DeclaratorMixin(_ParserSupport):
    """提供函数、参数、变量名称与声明形态的 source-level 判定。"""

    def _find_function_parameter_list(
        self, start: int, end: int
    ) -> tuple[int, int, int, int] | None:
        """找到声明中的主 function parameter list 及函数名区间。"""
        significant = self._significant(start, end)
        for position, index in enumerate(significant):
            if self.lexemes[index].text != "(" or index not in self._pairs:
                continue
            close = self._pairs[index]
            if close >= end or position == 0:
                continue
            name_end_token = significant[position - 1]
            name_start, name_end = self._function_name_range(start, name_end_token + 1)
            if name_start is None:
                continue
            name_text = self._text(name_start, name_end).strip()
            if name_text in _CONTROL or name_text in {
                "sizeof",
                "alignof",
                "decltype",
                "noexcept",
                "requires",
            }:
                continue
            return index, close, name_start, name_end
        return None

    def _function_name_range(self, start: int, end: int) -> tuple[int | None, int]:
        """识别普通函数名、析构名和 operator 名称的源码范围。"""
        last = self._previous_significant(end - 1, start)
        if last is None:
            return None, end
        if self.lexemes[last].kind == "identifier":
            before = self._previous_significant(last - 1, start)
            if before is not None and self.lexemes[before].text == "~":
                return before, last + 1
            operator_word = self._previous_significant(last - 1, start)
            if operator_word is not None and self.lexemes[operator_word].text == "operator":
                return operator_word, last + 1
            return last, last + 1
        before = self._previous_significant(last - 1, start)
        if before is not None and self.lexemes[before].text == "operator":
            return before, last + 1
        return None, end

    def _name_element(self, start: int, end: int) -> GreenElement:
        """为函数名范围选择 identifier/destructor_name/operator_name。"""
        text = self._text(start, end)
        stripped = text.strip()
        if stripped.startswith("operator"):
            return GreenNode(
                "operator_name",
                tuple(GreenChild(self.lexemes[index].green()) for index in range(start, end)),
                named=True,
            )
        if stripped.startswith("~"):
            return GreenNode(
                "destructor_name",
                tuple(GreenChild(self.lexemes[index].green()) for index in range(start, end)),
                named=True,
            )
        return GreenToken("identifier", stripped, named=True)

    def _prototype_is_function(
        self,
        start: int,
        end: int,
        open_paren: int,
        close_paren: int,
        name_start: int,
        context: str,
    ) -> bool:
        """区分函数声明和 `Type object(args);` 直接初始化。"""
        name_text = self._text(name_start, open_paren).strip()
        if context == "class":
            if name_text.startswith("operator") or name_text.startswith("~"):
                return True
            return self._parameter_list_looks_declarative(open_paren, close_paren)
        if name_text.startswith("operator"):
            return True
        return self._parameter_list_looks_declarative(open_paren, close_paren)

    def _parameter_list_looks_declarative(self, open_paren: int, close_paren: int) -> bool:
        """粗粒度判断括号内容更像参数声明还是构造实参。"""
        parts = self._split_top_level(open_paren + 1, close_paren, ",")
        if not parts:
            return True
        for start, end in parts:
            significant = self._significant(start, end)
            if not significant:
                continue
            if any(self.lexemes[index].kind in _LITERAL_KINDS for index in significant):
                return False
            if any(self.lexemes[index].text in {"+", "-", "/", "%", "?"} for index in significant):
                return False
            if len(significant) == 1 and self.lexemes[significant[0]].kind == "identifier":
                # `f(Type)` 合法，`object(arg)` 也可能；顶层按 C++ most-vexing-parse 倾向函数。
                continue
        return True

    def _find_parameter_name(self, start: int, end: int) -> int | None:
        """从参数 declarator 中定位名字，不把函数指针后面的参数类型误认成名字。"""
        significant = self._significant(start, end)
        if not significant:
            return None

        # 优先识别 `(*cb)` / `(&arr)` / `(C::*cb)` 这类嵌套 declarator。
        for index in significant:
            if self.lexemes[index].kind != "identifier" or self.lexemes[index].text in _TYPE_WORDS:
                continue
            before = self._previous_significant(index - 1, start)
            if before is not None and self.lexemes[before].text in {"*", "&", "&&"}:
                opening = self._enclosing_open(before, "(", start)
                if opening is not None:
                    return index

        candidates: list[int] = []
        angle_depth = 0
        for index in significant:
            text = self.lexemes[index].text
            if text == "<":
                angle_depth += 1
                continue
            if text == ">" and angle_depth:
                angle_depth -= 1
                continue
            if text == ">>" and angle_depth:
                angle_depth = max(0, angle_depth - 2)
                continue
            if angle_depth:
                continue
            if (
                self.lexemes[index].kind == "identifier"
                and self.lexemes[index].text not in _TYPE_WORDS
            ):
                before = self._previous_significant(index - 1, start)
                after = self._next_significant(index + 1, end)
                if before is not None and self.lexemes[before].text == "::":
                    continue
                if after is not None and self.lexemes[after].text == "::":
                    continue
                candidates.append(index)
        if not candidates:
            return None
        if len(candidates) == 1:
            first_word = self.lexemes[significant[0]].text
            if first_word in {"typename", "class"}:
                return candidates[0]
            # 单个自定义类型且没有 declarator 时通常是匿名参数。
            if candidates[0] == significant[0] and len(significant) == 1:
                return None
        return candidates[-1]

    def _find_variable_name(self, start: int, end: int) -> int | None:
        """识别常见变量 declarator 的名字，并忽略 initializer 内部的标识符。"""
        search_end = end
        equal = self._find_top_level_token(start, end, "=")
        if equal is not None:
            search_end = equal
        else:
            # direct-init/list-init 的第一个顶层括号属于 initializer，名字一定在它之前。
            for index in self._significant(start, end):
                if (
                    self.lexemes[index].text in {"(", "{"}
                    and index in self._pairs
                    and self._pairs[index] < end
                ):
                    search_end = index
                    break
        significant = self._significant(start, search_end)
        candidates: list[int] = []
        for position, index in enumerate(significant):
            if self.lexemes[index].kind != "identifier":
                continue
            word = self.lexemes[index].text
            if word in _TYPE_WORDS or word in _STORAGE or word in _QUALIFIERS:
                continue
            before = significant[position - 1] if position else None
            after = significant[position + 1] if position + 1 < len(significant) else None
            if before is not None and self.lexemes[before].text == "::":
                continue
            if after is not None and self.lexemes[after].text == "::":
                continue
            candidates.append(index)
        if (
            len(candidates) < 2
            and significant
            and self.lexemes[significant[0]].text not in (_TYPE_WORDS | _STORAGE | _QUALIFIERS)
        ):
            return None
        for index in reversed(candidates):
            after = self._next_significant(index + 1, search_end)
            if after is None or self.lexemes[after].text in {"=", "(", "{", "[", ",", ";"}:
                return index
        return candidates[-1] if len(candidates) >= 2 else None

    def _looks_like_declaration(self, start: int, end: int, *, context: str) -> bool:
        """用保守启发式判断一个分号单元是否像声明。

        C++ 的 `T * x;` 与 `a * b;` 在不知道名字语义时天然有歧义。这里不做
        typedef/name lookup：顶层和类作用域优先按声明；block 中仅在类型拼写具有
        明显 type-like 形态时把 `*`/`&` 解释为 declarator。
        """
        significant = self._significant(start, end)
        if not significant:
            return False
        first_index = significant[0]
        first = self.lexemes[first_index].text
        if first in _STORAGE | _QUALIFIERS | _TYPE_WORDS | {
            "constexpr",
            "consteval",
            "constinit",
            "using",
            "typedef",
        }:
            return True

        content_end = self._before_trailing_semicolon(start, end)
        name = self._find_variable_name(start, content_end)
        if name is None:
            return False

        # 名字之前出现真正的表达式运算符时，不再猜成声明。pointer/reference
        # punctuator 保留给 declarator。
        for index in self._significant(first_index + 1, name):
            text = self.lexemes[index].text
            if text in {
                "+",
                "-",
                "/",
                "%",
                "^",
                "|",
                "||",
                "and",
                "or",
                "xor",
                "?",
                "=",
                "==",
                "!=",
                "<=>",
            }:
                return False

        if context in {"top", "class"}:
            return True

        prefix = self._text(first_index, name).strip()
        first_word = self.lexemes[first_index].text
        if "::" in prefix or first_word.endswith("_t"):
            return True
        if first_word and first_word[0].isupper():
            return True

        # `Foo value;` 这类两个 identifier 连续出现，本身不构成合法普通表达式。
        before_name = self._previous_significant(name - 1, first_index)
        return (
            before_name is not None
            and self.lexemes[before_name].kind == "identifier"
        )

    def _specifier_replacements(self, start: int, end: int) -> list[_Replacement]:
        """把 storage/type qualifier 包装成稳定 named node，供 convenience view 查询。"""
        result: list[_Replacement] = []
        for index in self._significant(start, end):
            word = self.lexemes[index].text
            if word in _STORAGE:
                node = self._compose("storage_class_specifier", index, index + 1, [])
                result.append(_Replacement(index, index + 1, node))
            elif word in _QUALIFIERS:
                node = self._compose("type_qualifier", index, index + 1, [])
                result.append(_Replacement(index, index + 1, node))
        return result

    def _type_range(self, start: int, name_start: int) -> tuple[int, int] | None:
        """提取函数声明中 return type 的源码区间。"""
        first = self._next_significant(start, name_start)
        if first is None:
            return None
        while first < name_start and self.lexemes[first].text in _STORAGE | {
            "inline",
            "constexpr",
            "consteval",
            "extern",
            "friend",
            "virtual",
            "explicit",
        }:
            next_index = self._next_significant(first + 1, name_start)
            if next_index is None:
                return None
            first = next_index
        if first >= name_start:
            return None
        return first, name_start

    def _special_member_clause(self, start: int, end: int) -> _Replacement | None:
        """识别 `= delete` / `= default` 子句。"""
        equal = self._find_top_level_token(start, end, "=")
        if equal is None:
            return None
        word = self._next_significant(equal + 1, end)
        if word is None:
            return None
        text = self.lexemes[word].text
        if text not in {"delete", "default"}:
            return None
        kind = "delete_method_clause" if text == "delete" else "default_method_clause"
        node = self._compose(kind, equal, word + 1, [])
        return _Replacement(equal, word + 1, node)

    def _find_call_suffix(self, start: int, end: int) -> tuple[int, int] | None:
        """如果整个表达式以一次函敲调用结束，返回其实参括号。"""
        significant = self._significant(start, end)
        if len(significant) < 3:
            return None
        last = significant[-1]
        if self.lexemes[last].text != ")" or last not in self._reverse_pairs:
            return None
        opening = self._reverse_pairs[last]
        if opening <= significant[0]:
            return None
        before = self._previous_significant(opening - 1, start)
        if before is None:
            return None
        if self.lexemes[before].kind == "identifier" or self.lexemes[before].text in {
            ">",
            ")",
            "]",
        }:
            return opening, last
        return None
