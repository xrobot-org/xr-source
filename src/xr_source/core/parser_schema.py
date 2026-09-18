"""定义具体 parser 运行时暴露的 kind 与 field 标识表。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParserKindInfo:
    """记录具体 parser 的 kind id、名称以及 named 属性。"""
    id: int
    name: str
    named: bool


@dataclass(frozen=True, slots=True)
class ParserSchema:
    """保存具体 parser 运行时导出的 kind 与 field 标识集合。"""

    language: str
    kinds: tuple[ParserKindInfo, ...]
    fields: tuple[str, ...]

    def kind(self, name: str) -> ParserKindInfo | None:
        """按 kind 名称查询具体 parser 暴露的运行时 kind 信息。"""
        return next((kind for kind in self.kinds if kind.name == name), None)

    @property
    def kind_names(self) -> frozenset[str]:
        """返回当前 parser 运行时导出的全部 kind 名称。"""
        return frozenset(kind.name for kind in self.kinds)
