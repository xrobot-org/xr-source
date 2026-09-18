"""定义语言无关的结构 grammar 合同。\n\n既支持原生 C++ grammar，也支持从 node-types 元数据加载其他语言。\n"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any

# ---------------------------------------------------------------------------
# 语言无关的 grammar 结构合同
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GrammarTypeRef:
    """用 kind 和 named/anonymous 属性唯一标识一种 grammar 类型。\n\n    named 位属于类型身份的一部分。\n    """
    kind: str
    named: bool


@dataclass(frozen=True, slots=True)
class GrammarSlot:
    """描述一个 grammar 字段或通用 children 槽允许出现的类型及数量约束。"""
    multiple: bool
    required: bool
    types: tuple[GrammarTypeRef, ...]

    def accepts(self, kind: str, *, named: bool) -> bool:
        """判断该 grammar 槽是否直接允许指定 kind/named 组合。"""
        return GrammarTypeRef(kind, named) in self.types


@dataclass(frozen=True)
class GrammarNodeSpec:
    """描述一种语法 kind 的 grammar 元数据。\n\n    包含字段、children、root 和 subtype 关系；它不是实际解析得到的源码节点。\n    """
    kind: str
    named: bool
    root: bool = False
    fields: tuple[tuple[str, GrammarSlot], ...] = ()
    children: GrammarSlot | None = None
    subtypes: tuple[GrammarTypeRef, ...] = ()

    @cached_property
    def field_names(self) -> tuple[str, ...]:
        """按确定顺序返回该节点合同声明的 field 名称。"""
        return tuple(name for name, _ in self.fields)

    def field(self, name: str) -> GrammarSlot | None:
        """返回指定 field 的结构合同；不存在时返回 None。"""
        return next((slot for field_name, slot in self.fields if field_name == name), None)


@dataclass(frozen=True)
class LanguageGrammar:
    """表示与具体 parser 运行时对象解耦的语言结构 grammar。\n\n    该对象可版本追踪，并保留来源 revision 与校验信息。\n    """
    language: str
    version: str
    source_revision: str
    source_sha256: str
    nodes: tuple[GrammarNodeSpec, ...]

    @cached_property
    def _node_map(self) -> dict[tuple[str, bool], GrammarNodeSpec]:
        """构建并缓存从 (kind, named) 到 GrammarNodeSpec 的查找表。"""
        return {(node.kind, node.named): node for node in self.nodes}

    @cached_property
    def kind_names(self) -> frozenset[str]:
        """返回该 grammar 中出现过的全部 kind 拼写。"""
        return frozenset(node.kind for node in self.nodes)

    @cached_property
    def roots(self) -> tuple[GrammarNodeSpec, ...]:
        """返回被标记为合法源码根节点的 grammar kind。"""
        return tuple(node for node in self.nodes if node.root)

    def node(
        self,
        kind: str,
        *,
        named: bool | None = None,
    ) -> GrammarNodeSpec | None:
        """按 kind 和可选 named 属性查找 grammar 节点合同。"""
        if named is not None:
            return self._node_map.get((kind, named))
        matches = tuple(
            node
            for (candidate, _), node in self._node_map.items()
            if candidate == kind
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError(
                f"{self.language} grammar kind {kind!r} is ambiguous; specify named="
            )
        return matches[0]

    def require_node(
        self,
        kind: str,
        *,
        named: bool | None = None,
    ) -> GrammarNodeSpec:
        """查找指定 grammar 节点合同；不存在或身份不明确时抛出 KeyError。"""
        node = self.node(kind, named=named)
        if node is None:
            suffix = "" if named is None else f", named={named}"
            raise KeyError(f"unknown {self.language} grammar kind {kind!r}{suffix}")
        return node

    def subtype_refs(
        self,
        kind: str,
        *,
        named: bool = True,
    ) -> tuple[GrammarTypeRef, ...]:
        """返回某个抽象 grammar kind 直接声明的 subtype 引用。"""
        return self.require_node(kind, named=named).subtypes

    def is_subtype(
        self,
        actual_kind: str,
        expected_kind: str,
        *,
        actual_named: bool = True,
        expected_named: bool = True,
    ) -> bool:
        """仅依据 grammar 元数据判断实际 kind 是否属于期望 kind 的传递 subtype。"""
        actual = GrammarTypeRef(actual_kind, actual_named)
        expected = GrammarTypeRef(expected_kind, expected_named)
        if actual == expected:
            return True

        visited: set[GrammarTypeRef] = set()
        pending = [expected]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            spec = self.node(current.kind, named=current.named)
            if spec is None:
                continue
            if actual in spec.subtypes:
                return True
            pending.extend(spec.subtypes)
        return False

        # node-types.json 被视为可版本追踪的源数据，而不是复制成手写类层次。
        # 这样 grammar 升级时差异可以直接审计。
    @classmethod
    def from_node_types(
        cls,
        *,
        language: str,
        version: str,
        source_revision: str,
        source_sha256: str,
        data: list[dict[str, Any]],
    ) -> LanguageGrammar:
        """从解码后的 node-types 数据验证并构建版本化 LanguageGrammar。"""
        nodes = tuple(_node_spec(item) for item in data)
        keys = [(node.kind, node.named) for node in nodes]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{language} node-types contains duplicate type identities")
        return cls(
            language=language,
            version=version,
            source_revision=source_revision,
            source_sha256=source_sha256,
            nodes=nodes,
        )


def _type_ref(data: dict[str, Any]) -> GrammarTypeRef:
    """把一条 node-types 类型描述转换为 GrammarTypeRef。"""
    return GrammarTypeRef(
        kind=_string(data, "type"),
        named=_bool(data, "named"),
    )


def _slot(data: dict[str, Any]) -> GrammarSlot:
    """把 node-types 中的 field/children 描述转换为 GrammarSlot。"""
    raw_types = data.get("types", [])
    if not isinstance(raw_types, list):
        raise TypeError("grammar slot types must be a list")
    return GrammarSlot(
        multiple=_bool(data, "multiple"),
        required=_bool(data, "required"),
        types=tuple(_type_ref(item) for item in raw_types),
    )


def _node_spec(data: dict[str, Any]) -> GrammarNodeSpec:
    """把一条 node-types 节点描述转换为 GrammarNodeSpec。"""
    raw_fields = data.get("fields", {})
    if not isinstance(raw_fields, dict):
        raise TypeError("grammar node fields must be a mapping")

    raw_subtypes = data.get("subtypes", [])
    if not isinstance(raw_subtypes, list):
        raise TypeError("grammar node subtypes must be a list")

    raw_children = data.get("children")
    if raw_children is not None and not isinstance(raw_children, dict):
        raise TypeError("grammar node children must be a mapping")

    return GrammarNodeSpec(
        kind=_string(data, "type"),
        named=_bool(data, "named"),
        root=bool(data.get("root", False)),
        fields=tuple(
            (name, _slot(spec))
            for name, spec in sorted(raw_fields.items())
        ),
        children=None if raw_children is None else _slot(raw_children),
        subtypes=tuple(_type_ref(item) for item in raw_subtypes),
    )


def _string(data: dict[str, Any], key: str) -> str:
    """读取 grammar 字段并确保其值是字符串。"""
    value = data.get(key)
    if not isinstance(value, str):
        raise TypeError(f"grammar {key} must be a string")
    return value


def _bool(data: dict[str, Any], key: str) -> bool:
    """读取 grammar 字段并确保其值是布尔值。"""
    value = data.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"grammar {key} must be a boolean")
    return value
