from __future__ import annotations

from tree_sitter import Language, Node, Parser

from xr_source.core.diagnostic import Diagnostic
from xr_source.core.green import (
    GreenChild,
    GreenElement,
    GreenNode,
    GreenToken,
    GreenTrivia,
)
from xr_source.core.parser_schema import ParserKindInfo, ParserSchema
from xr_source.core.span import SourcePoint, SourceSpan
from xr_source.core.text import decode_source
from xr_source.core.tree import SyntaxTree


class TreeSitterSyntaxParser:
    __slots__ = ("_language_name", "_language", "_parser", "_schema")

    def __init__(self, language_name: str, language: Language) -> None:
        self._language_name = language_name
        self._language = language
        self._parser = Parser(language)
        self._schema = _schema(language_name, language)

    @property
    def schema(self) -> ParserSchema:
        return self._schema

    def parse(self, source: str | bytes, *, source_name: str | None = None) -> SyntaxTree:
        data = source.encode("utf-8") if isinstance(source, str) else bytes(source)
        parsed = self._parser.parse(data)
        root_node = parsed.root_node
        root = self._convert(root_node, data, force_node=True)
        if not isinstance(root, GreenNode):
            raise AssertionError("Tree-sitter root must map to a GreenNode")

        if root_node.start_byte or root_node.end_byte != len(data):
            children = list(root.children)
            if root_node.start_byte:
                children.insert(0, GreenChild(_gap(data[: root_node.start_byte])))
            if root_node.end_byte < len(data):
                children.append(GreenChild(_gap(data[root_node.end_byte :])))
            root = GreenNode(
                root.kind,
                tuple(children),
                root.named,
                root.missing,
                root.error,
            )

        result = SyntaxTree(
            self._language_name,
            root,
            tuple(self._diagnostics(root_node)),
            source_name,
        )
        if result.render_bytes() != data:
            raise AssertionError("lossless parser invariant violated")
        return result

    def _convert(
        self,
        node: Node,
        source: bytes,
        *,
        force_node: bool = False,
    ) -> GreenElement:
        if node.child_count == 0 and not force_node:
            return GreenToken(
                node.type,
                decode_source(source[node.start_byte : node.end_byte]),
                named=node.is_named,
                missing=node.is_missing,
                error=node.is_error,
            )

        children: list[GreenChild] = []
        cursor = node.start_byte
        for index in range(node.child_count):
            child = node.child(index)
            if child is None:
                continue
            if child.start_byte > cursor:
                children.append(GreenChild(_gap(source[cursor : child.start_byte])))
            if child.start_byte < cursor:
                raise AssertionError(
                    f"overlapping Tree-sitter children in {node.type}: "
                    f"{child.start_byte} < {cursor}"
                )
            children.append(
                GreenChild(
                    self._convert(child, source),
                    node.field_name_for_child(index),
                )
            )
            cursor = child.end_byte

        if cursor < node.end_byte:
            children.append(GreenChild(_gap(source[cursor : node.end_byte])))
        return GreenNode(
            node.type,
            tuple(children),
            named=node.is_named,
            missing=node.is_missing,
            error=node.is_error,
        )

    @staticmethod
    def _diagnostics(root: Node) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        stack = [root]
        while stack:
            node = stack.pop()
            if node.is_error or node.is_missing:
                diagnostics.append(
                    Diagnostic(
                        "missing syntax" if node.is_missing else "syntax error",
                        SourceSpan(node.start_byte, node.end_byte),
                        SourcePoint(node.start_point.row, node.start_point.column),
                        SourcePoint(node.end_point.row, node.end_point.column),
                    )
                )
            stack.extend(reversed(node.children))
        return diagnostics


def _schema(language_name: str, language: Language) -> ParserSchema:
    kinds = tuple(
        ParserKindInfo(
            id=index,
            name=_required_name(
                language.node_kind_for_id(index),
                f"node kind {index}",
            ),
            named=language.node_kind_is_named(index),
        )
        for index in range(language.node_kind_count)
    )
    fields = tuple(
        _required_name(
            language.field_name_for_id(index),
            f"field {index}",
        )
        for index in range(1, language.field_count + 1)
    )
    return ParserSchema(language_name, kinds, fields)


def _required_name(value: str | None, description: str) -> str:
    if value is None:
        raise RuntimeError(f"Tree-sitter did not expose a name for {description}")
    return value


def _gap(data: bytes) -> GreenTrivia:
    text = decode_source(data)
    if text.isspace():
        kind = "newline" if "\n" in text or "\r" in text else "whitespace"
    else:
        kind = "raw"
    return GreenTrivia(kind, text)
