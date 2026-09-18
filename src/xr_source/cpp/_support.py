"""Native C++ parser 各结构阶段共享的严格类型合同。

这些方法由最终的 _StructuralParser 通过 mixin 组合提供。这里不实现行为，只让
mypy 能在单独检查每个 mixin 时看到完整接口；运行时 MRO 会优先命中真实实现。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from xr_source.core import Diagnostic, GreenElement, GreenNode

from .lexer import _Lexeme

if TYPE_CHECKING:
    from ._ranges import _Replacement


class _ParserSupport:
    """描述 native parser mixin 之间互相依赖的内部接口。"""

    lexemes: Sequence[_Lexeme]
    diagnostics: list[Diagnostic]
    _pairs: dict[int, int]
    _reverse_pairs: dict[int, int]

    def _significant(self, start: int, end: int) -> list[int]:
        """返回区间内非 trivia/comment 的 lexeme 索引。"""
        raise NotImplementedError

    def _next_significant(self, start: int, end: int) -> int | None:
        """向右寻找下一个有效 lexeme。"""
        raise NotImplementedError

    def _previous_significant(self, start: int, lower_bound: int) -> int | None:
        """向左寻找上一个有效 lexeme。"""
        raise NotImplementedError

    def _split_top_level(
        self,
        start: int,
        end: int,
        separator: str,
    ) -> list[tuple[int, int]]:
        """按不位于嵌套分隔符内的 separator 拆分区间。"""
        raise NotImplementedError

    def _find_top_level_token(
        self,
        start: int,
        end: int,
        token: str,
    ) -> int | None:
        """查找当前层级的指定 token。"""
        raise NotImplementedError

    def _enclosing_open(
        self,
        index: int,
        token: str,
        lower_bound: int,
    ) -> int | None:
        """查找包围当前位置的指定开分隔符。"""
        raise NotImplementedError

    def _before_trailing_semicolon(self, start: int, end: int) -> int:
        """返回排除尾部分号后的区间末端。"""
        raise NotImplementedError

    def _trim(self, start: int, end: int) -> tuple[int, int] | None:
        """去除区间两端 trivia/comment。"""
        raise NotImplementedError

    def _text(self, start: int, end: int) -> str:
        """还原 lexeme 区间源码文本。"""
        raise NotImplementedError

    def _compose(
        self,
        kind: str,
        start: int,
        end: int,
        replacements: Iterable[_Replacement],
    ) -> GreenNode:
        """把不重叠 replacement 组合成 green node。"""
        raise NotImplementedError

    def _lowest_precedence_operator(self, start: int, end: int) -> int | None:
        """查找顶层最低优先级运算符。"""
        raise NotImplementedError

    def _find_call_suffix(self, start: int, end: int) -> tuple[int, int] | None:
        """识别覆盖整个表达式的调用实参括号。"""
        raise NotImplementedError

    def _parse_scope(
        self,
        start: int,
        end: int,
        *,
        context: str,
    ) -> list[_Replacement]:
        """解析连续源码作用域。"""
        raise NotImplementedError

    def _parse_expression(self, start: int, end: int) -> GreenElement:
        """解析表达式结构。"""
        raise NotImplementedError

    def _expression_replacement(
        self,
        start: int,
        end: int,
        field: str | None = None,
    ) -> _Replacement | None:
        """构造不吞掉 expression 两端 trivia 的 replacement。"""
        raise NotImplementedError

    def _parse_compound(self, open_brace: int, close_brace: int) -> GreenNode:
        """解析复合语句。"""
        raise NotImplementedError

    def _parse_return(self, start: int, end: int) -> _Replacement:
        """解析 return 语句。"""
        raise NotImplementedError

    def _parse_control(
        self,
        start: int,
        end: int,
        keyword: str,
    ) -> _Replacement:
        """解析控制流语句。"""
        raise NotImplementedError

    def _parse_do(self, start: int, end: int) -> _Replacement:
        """解析 do/while 语句。"""
        raise NotImplementedError

    def _parse_concept(self, start: int, end: int) -> _Replacement:
        """解析 concept 定义。"""
        raise NotImplementedError

    def _find_function_parameter_list(
        self,
        start: int,
        end: int,
    ) -> tuple[int, int, int, int] | None:
        """定位函数主参数列表与函数名范围。"""
        raise NotImplementedError

    def _prototype_is_function(
        self,
        start: int,
        end: int,
        open_paren: int,
        close_paren: int,
        name_start: int,
        context: str,
    ) -> bool:
        """区分函数声明与直接初始化。"""
        raise NotImplementedError

    def _name_element(self, start: int, end: int) -> GreenElement:
        """构造函数名/析构名/operator 名称元素。"""
        raise NotImplementedError

    def _find_parameter_name(self, start: int, end: int) -> int | None:
        """定位参数 declarator 名称。"""
        raise NotImplementedError

    def _find_variable_name(self, start: int, end: int) -> int | None:
        """定位变量 declarator 名称。"""
        raise NotImplementedError

    def _looks_like_declaration(
        self,
        start: int,
        end: int,
        *,
        context: str,
    ) -> bool:
        """保守判断源码单元是否属于声明。"""
        raise NotImplementedError

    def _specifier_replacements(
        self,
        start: int,
        end: int,
    ) -> list[_Replacement]:
        """返回 storage/type qualifier 的结构化 replacement。"""
        raise NotImplementedError

    def _type_range(
        self,
        start: int,
        name_start: int,
    ) -> tuple[int, int] | None:
        """提取函数返回类型源码区间。"""
        raise NotImplementedError

    def _special_member_clause(
        self,
        start: int,
        end: int,
    ) -> _Replacement | None:
        """识别 = delete/default 子句。"""
        raise NotImplementedError
