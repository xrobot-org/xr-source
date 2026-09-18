"""xr-source 自有 C++ 结构解析器。

该 parser 不依赖 tree-sitter/Clang；只建立 source-level syntax structure，
不实现名字查找、重载决议、模板实例化或类型推导。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from xr_source.core import (
    Diagnostic,
    GreenNode,
    GreenToken,
    ParserKindInfo,
    ParserSchema,
    SyntaxTree,
    decode_source,
)

from ._declaration import _DeclarationMixin
from ._declarator import _DeclaratorMixin
from ._expression import _ExpressionMixin
from ._ranges import _deduplicate_replacements, _RangeMixin, _Replacement
from .grammar import CPP_GRAMMAR
from .lexer import _PUNCTUATORS, _QUALIFIERS, _STORAGE, _TYPE_WORDS, _Lexeme, _Lexer


class CppParser:
    """不依赖第三方 parser runtime 的 lossless C++ source parser。"""

    grammar = CPP_GRAMMAR

    def __init__(self) -> None:
        """初始化 parser，并构造稳定的运行时 kind/field 表。"""
        refs: set[tuple[str, bool]] = {(node.kind, node.named) for node in self.grammar.nodes}
        for node in self.grammar.nodes:
            refs.update((item.kind, item.named) for item in node.subtypes)
            if node.children is not None:
                refs.update((item.kind, item.named) for item in node.children.types)
            for _, slot in node.fields:
                refs.update((item.kind, item.named) for item in slot.types)
        refs.update((punctuator, False) for punctuator in _PUNCTUATORS)
        refs.update((word, False) for word in _TYPE_WORDS | _STORAGE | _QUALIFIERS)
        ordered = sorted(refs, key=lambda item: (item[0], item[1]))
        fields = sorted(
            {field_name for node in self.grammar.nodes for field_name, _ in node.fields}
        )
        self._schema = ParserSchema(
            "cpp",
            tuple(
                ParserKindInfo(index, name, named) for index, (name, named) in enumerate(ordered)
            ),
            tuple(fields),
        )

    @property
    def schema(self) -> ParserSchema:
        """返回 xr-source native C++ parser 的 kind/field 表。"""
        return self._schema

    def parse(self, source: str | bytes, *, source_name: str | None = None) -> SyntaxTree:
        """解析源码并保证结果可逐字节还原。"""
        data = source.encode("utf-8") if isinstance(source, str) else bytes(source)
        text = decode_source(data)
        lexer = _Lexer(text)
        lexemes, diagnostics = lexer.scan()
        parser = _StructuralParser(lexemes, diagnostics)
        root = parser.parse_translation_unit()
        tree = SyntaxTree("cpp", root, tuple(parser.diagnostics), source_name)
        if tree.render_bytes() != data:
            raise AssertionError("native C++ parser 破坏了 lossless round-trip 不变量")
        return tree


class _StructuralParser(_DeclarationMixin, _ExpressionMixin, _DeclaratorMixin, _RangeMixin):
    def __init__(self, lexemes: Sequence[_Lexeme], diagnostics: Iterable[Diagnostic]) -> None:
        """保存词法结果并建立括号配对表。"""
        self.lexemes = tuple(lexemes)
        self.diagnostics = list(diagnostics)
        self._pairs: dict[int, int] = {}
        self._reverse_pairs: dict[int, int] = {}
        self._build_delimiter_pairs()

    def parse_translation_unit(self) -> GreenNode:
        """解析整个 translation unit；未知顶层片段原样保留。"""
        replacements = self._parse_scope(0, len(self.lexemes), context="top")
        return self._compose("translation_unit", 0, len(self.lexemes), replacements)

    def _build_delimiter_pairs(self) -> None:
        """对 (), [] 和 {} 建立配对，并对不平衡输入产生诊断。"""
        opens = {"(": ")", "[": "]", "{": "}"}
        closes = {value: key for key, value in opens.items()}
        stack: list[tuple[str, int]] = []
        for index, item in enumerate(self.lexemes):
            if item.trivia or item.kind == "comment":
                continue
            text = item.text
            if text in opens:
                stack.append((text, index))
            elif text in closes:
                if not stack or stack[-1][0] != closes[text]:
                    self._diagnostic("不匹配的闭合符号", index, index + 1)
                    continue
                _, opening = stack.pop()
                self._pairs[opening] = index
                self._reverse_pairs[index] = opening
        for _, opening in stack:
            self._diagnostic("未闭合的分隔符", opening, opening + 1)

    def _parse_scope(self, start: int, end: int, *, context: str) -> list[_Replacement]:
        """按顶层语句/声明边界解析一个连续作用域。"""
        result: list[_Replacement] = []
        cursor = start
        while True:
            current = self._next_significant(cursor, end)
            if current is None:
                break

            if self.lexemes[current].text == "#" and self._line_prefix_is_trivia(current, start):
                replacement = self._parse_preprocessor(current, end)
                result.append(replacement)
                cursor = replacement.end
                continue

            if self.lexemes[current].text == "template":
                replacement = self._parse_template(current, end, context=context)
                if replacement is not None:
                    result.append(replacement)
                    cursor = replacement.end
                    continue

            if self.lexemes[current].text in {"class", "struct", "union"}:
                replacement = self._parse_class(current, end)
                if replacement is not None:
                    result.append(replacement)
                    cursor = replacement.end
                    semicolon = self._next_significant(cursor, end)
                    if semicolon is not None and self.lexemes[semicolon].text == ";":
                        cursor = semicolon + 1
                    continue

            if self.lexemes[current].text == "namespace":
                replacement = self._parse_namespace(current, end)
                if replacement is not None:
                    result.append(replacement)
                    cursor = replacement.end
                    continue

            if context == "class" and self.lexemes[current].text in {
                "public",
                "private",
                "protected",
            }:
                colon = self._next_significant(current + 1, end)
                if colon is not None and self.lexemes[colon].text == ":":
                    node = self._compose("access_specifier", current, colon + 1, [])
                    result.append(_Replacement(current, colon + 1, node))
                    cursor = colon + 1
                    continue

            unit_end = self._find_unit_end(current, end, context=context)
            if unit_end <= current:
                cursor = current + 1
                continue
            replacement = self._parse_unit(current, unit_end, context=context)
            if replacement is not None:
                result.append(replacement)
            cursor = unit_end
        return _deduplicate_replacements(result)

    def _parse_preprocessor(self, start: int, end: int) -> _Replacement:
        """解析一条逻辑预处理行，并对 #include 暴露 path field。"""
        line_end = start + 1
        while line_end < end:
            item = self.lexemes[line_end]
            if item.kind == "newline":
                # 与既有 API 保持一致：directive 节点拥有本行换行。
                # lexer 已保证这里只包含一个 CR/LF/CRLF，不会吞掉下一空行。
                line_end += 1
                break
            line_end += 1

        significant = self._significant(start, line_end)
        keyword = self.lexemes[significant[1]].text if len(significant) > 1 else ""
        kind = {
            "include": "preproc_include",
            "define": "preproc_def",
            "if": "preproc_if",
            "ifdef": "preproc_ifdef",
            "ifndef": "preproc_ifdef",
        }.get(keyword, "preproc_call")
        replacements: list[_Replacement] = []

        if kind == "preproc_include" and len(significant) > 2:
            path_start = significant[2]
            if self.lexemes[path_start].text == "<":
                path_end = path_start + 1
                while path_end < line_end and self.lexemes[path_end].text != ">":
                    path_end += 1
                if path_end < line_end:
                    path_end += 1
                    text = self._text(path_start, path_end)
                    replacements.append(
                        _Replacement(
                            path_start,
                            path_end,
                            GreenToken("system_lib_string", text, named=True),
                            "path",
                        )
                    )
            else:
                token = self.lexemes[path_start]
                replacements.append(_Replacement(path_start, path_start + 1, token.green(), "path"))

        node = self._compose(kind, start, line_end, replacements)
        return _Replacement(start, line_end, node)

    def _parse_template(self, start: int, end: int, *, context: str) -> _Replacement | None:
        """解析 template<...> 及其紧随的声明。"""
        open_angle = self._next_significant(start + 1, end)
        if open_angle is None or self.lexemes[open_angle].text != "<":
            return None
        close_angle = self._match_angle(open_angle, end)
        if close_angle is None:
            return None
        parameters = self._parse_template_parameters(open_angle, close_angle)
        declaration_start = self._next_significant(close_angle + 1, end)
        if declaration_start is None:
            return None

        declaration_end = self._find_unit_end(declaration_start, end, context=context)
        if declaration_end <= declaration_start:
            return None

        if self.lexemes[declaration_start].text in {"class", "struct", "union"}:
            nested = self._parse_class(declaration_start, declaration_end)
        else:
            nested = self._parse_unit(declaration_start, declaration_end, context=context)
        if nested is None:
            return None

        node = self._compose(
            "template_declaration",
            start,
            declaration_end,
            [
                _Replacement(open_angle, close_angle + 1, parameters, "parameters"),
                _Replacement(nested.start, nested.end, nested.element),
            ],
        )
        return _Replacement(start, declaration_end, node)

    def _parse_template_parameters(self, open_angle: int, close_angle: int) -> GreenNode:
        """把模板参数列表拆成带 name/default 的参数节点。"""
        replacements: list[_Replacement] = []
        for part_start, part_end in self._split_top_level(open_angle + 1, close_angle, ","):
            if self._next_significant(part_start, part_end) is None:
                continue
            node = self._parse_parameter(part_start, part_end, template=True)
            replacements.append(_Replacement(part_start, part_end, node))
        return self._compose(
            "template_parameter_list",
            open_angle,
            close_angle + 1,
            replacements,
        )

    def _parse_class(self, start: int, end: int) -> _Replacement | None:
        """解析 class/struct/union 定义并递归解析成员列表。"""
        keyword = self.lexemes[start].text
        significant = self._significant(start + 1, end)
        name_index = next(
            (index for index in significant if self.lexemes[index].kind == "identifier"),
            None,
        )
        open_brace = next(
            (index for index in significant if self.lexemes[index].text == "{"),
            None,
        )
        if open_brace is None or open_brace not in self._pairs:
            return None
        close_brace = self._pairs[open_brace]
        if close_brace >= end:
            return None

        body_replacements = self._parse_scope(open_brace + 1, close_brace, context="class")
        body = self._compose(
            "field_declaration_list",
            open_brace,
            close_brace + 1,
            body_replacements,
        )
        replacements = [_Replacement(open_brace, close_brace + 1, body, "body")]
        if name_index is not None and name_index < open_brace:
            replacements.append(
                _Replacement(
                    name_index,
                    name_index + 1,
                    GreenToken("type_identifier", self.lexemes[name_index].text, named=True),
                    "name",
                )
            )
        kind = {
            "class": "class_specifier",
            "struct": "struct_specifier",
            "union": "union_specifier",
        }[keyword]
        class_end = close_brace + 1
        node = self._compose(kind, start, class_end, replacements)

        # 普通顶层/成员 class 声明的分号不属于 specifier；保持与原 view 兼容。
        return _Replacement(start, class_end, node)

    def _parse_namespace(self, start: int, end: int) -> _Replacement | None:
        """解析 namespace body，使内部声明仍可结构化查询。"""
        significant = self._significant(start + 1, end)
        open_brace = next((i for i in significant if self.lexemes[i].text == "{"), None)
        if open_brace is None or open_brace not in self._pairs:
            return None
        close_brace = self._pairs[open_brace]
        replacements = self._parse_scope(open_brace + 1, close_brace, context="top")
        body = self._compose("declaration_list", open_brace, close_brace + 1, replacements)
        nested: list[_Replacement] = [_Replacement(open_brace, close_brace + 1, body, "body")]
        name = next(
            (i for i in significant if i < open_brace and self.lexemes[i].kind == "identifier"),
            None,
        )
        if name is not None:
            nested.append(_Replacement(name, name + 1, self.lexemes[name].green(), "name"))
        node = self._compose("namespace_definition", start, close_brace + 1, nested)
        return _Replacement(start, close_brace + 1, node)
