"""定义语法节点和诊断共同使用的字节范围与行列位置。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class SourcePoint:
    """表示 parser 报告的零基行号和列号位置。"""
    row: int
    column: int


@dataclass(frozen=True, slots=True, order=True)
class SourceSpan:
    """表示原始源码编码中的半开字节区间 [start, end)。"""
    start: int
    end: int

    def __post_init__(self) -> None:
        """校验半开字节区间满足 start >= 0 且 end >= start。"""
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid source span [{self.start}, {self.end})")

    @property
    def length(self) -> int:
        """返回该半开区间覆盖的字节数量。"""
        return self.end - self.start

    def contains(self, offset: int) -> bool:
        """判断给定字节偏移是否位于该半开区间内。"""
        return self.start <= offset < self.end
