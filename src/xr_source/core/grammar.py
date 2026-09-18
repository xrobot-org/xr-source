from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any


@dataclass(frozen=True, slots=True)
class GrammarTypeRef:
    kind: str
    named: bool


@dataclass(frozen=True, slots=True)
class GrammarSlot:
    multiple: bool
    required: bool
    types: tuple[GrammarTypeRef, ...]

    def accepts(self, kind: str, *, named: bool) -> bool:
        return GrammarTypeRef(kind, named) in self.types


@dataclass(frozen=True)
class GrammarNodeSpec:
    kind: str
    named: bool
    root: bool = False
    fields: tuple[tuple[str, GrammarSlot], ...] = ()
    children: GrammarSlot | None = None
    subtypes: tuple[GrammarTypeRef, ...] = ()

    @cached_property
    def field_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.fields)

    def field(self, name: str) -> GrammarSlot | None:
        return next((slot for field_name, slot in self.fields if field_name == name), None)


@dataclass(frozen=True)
class LanguageGrammar:
    language: str
    version: str
    source_revision: str
    source_sha256: str
    nodes: tuple[GrammarNodeSpec, ...]

    @cached_property
    def _node_map(self) -> dict[tuple[str, bool], GrammarNodeSpec]:
        return {(node.kind, node.named): node for node in self.nodes}

    @cached_property
    def kind_names(self) -> frozenset[str]:
        return frozenset(node.kind for node in self.nodes)

    @cached_property
    def roots(self) -> tuple[GrammarNodeSpec, ...]:
        return tuple(node for node in self.nodes if node.root)

    def node(
        self,
        kind: str,
        *,
        named: bool | None = None,
    ) -> GrammarNodeSpec | None:
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
        return self.require_node(kind, named=named).subtypes

    def is_subtype(
        self,
        actual_kind: str,
        expected_kind: str,
        *,
        actual_named: bool = True,
        expected_named: bool = True,
    ) -> bool:
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
    return GrammarTypeRef(
        kind=_string(data, "type"),
        named=_bool(data, "named"),
    )


def _slot(data: dict[str, Any]) -> GrammarSlot:
    raw_types = data.get("types", [])
    if not isinstance(raw_types, list):
        raise TypeError("grammar slot types must be a list")
    return GrammarSlot(
        multiple=_bool(data, "multiple"),
        required=_bool(data, "required"),
        types=tuple(_type_ref(item) for item in raw_types),
    )


def _node_spec(data: dict[str, Any]) -> GrammarNodeSpec:
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
    value = data.get(key)
    if not isinstance(value, str):
        raise TypeError(f"grammar {key} must be a string")
    return value


def _bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"grammar {key} must be a boolean")
    return value
