"""把可选 Tree-sitter 后端转换为 xr-source 的无损 green 语法树；当前仅供 CMake 等可选前端使用。

Lossless adapter from Tree-sitter parse trees into xr-source green syntax trees.
"""

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

# ---------------------------------------------------------------------------
# Tree-sitter -> xr-source 无损语法树转换
# EN: Tree-sitter -> lossless xr-source conversion
# ---------------------------------------------------------------------------

class TreeSitterSyntaxParser:
    """把可选 Tree-sitter CST 转换为 xr-source 无损 green tree。

    转换时显式补齐 parser 未覆盖的字节间隙并保留 field 标签；当前主要服务 CMake。

    Convert a Tree-sitter concrete syntax tree into the xr-source lossless model.

    Tree-sitter omits whitespace and some unparsed byte ranges from its child list.
    The adapter fills every gap with GreenTrivia and asserts render_bytes() equals
    the exact input. Tree-sitter Node objects never escape this module.
    """
    __slots__ = ("_language_name", "_language", "_parser", "_schema")

    def __init__(self, language_name: str, language: Language) -> None:
        """绑定语言名称与 Tree-sitter Language，并缓存运行时 schema。

        Bind the language name and Tree-sitter Language object and cache the runtime schema.
        """
        self._language_name = language_name
        self._language = language
        self._parser = Parser(language)
        self._schema = _schema(language_name, language)

    @property
    def schema(self) -> ParserSchema:
        """返回已加载 Tree-sitter parser 的 kind/field 运行时标识。

        Expose runtime kind/field identifiers from the loaded parser binary.
        """
        return self._schema

    def parse(self, source: str | bytes, *, source_name: str | None = None) -> SyntaxTree:
        """解析源码、补齐 parser 间隙为 trivia，并强制检查逐字节 round-trip。

        Parse source into an immutable SyntaxTree while enforcing byte-for-byte fidelity.
        """
        data = source.encode("utf-8") if isinstance(source, str) else bytes(source)
        parsed = self._parser.parse(data)
        root_node = parsed.root_node
        # 即使输入为空，translation unit 在结构上仍是根 node，而不是零宽 token。
        # force_node 用于在空文件场景保持这一结构区别。
        # EN: Even an empty translation unit is structurally a root *node*, not a
        # EN: zero-width token. force_node preserves that distinction for empty files.
        root = self._convert(root_node, data, force_node=True)
        if not isinstance(root, GreenNode):
            raise AssertionError("Tree-sitter root must map to a GreenNode")

        # 错误恢复可能产生不能覆盖完整输入的 root。root 范围外的字节必须
        # 显式保存为 trivia，不能因为 parser 没覆盖就静默丢失。
        # EN: Error recovery may produce a root that does not span the complete input.
        # EN: Preserve any bytes outside the parser root as trivia instead of dropping them.
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
        # 这是 adapter 最重要的安全不变量：允许 parser 产生诊断，
        # 但绝不允许在没有报错的情况下丢失源码字节。
        # EN: This is the central safety property of the adapter. Parser diagnostics
        # EN: are allowed; silent source loss is not.
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
        """递归把 Tree-sitter Node 转换为 GreenNode/GreenToken，并保留 child field。

        Recursively convert a Tree-sitter Node into GreenNode/GreenToken structure while
        preserving child fields.
        """
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
                # Tree-sitter 会主动省略空白，并可能在错误恢复时跳过其他字节。
                # 这些 gap 必须变成一等 GreenTrivia，保证 green tree 对源码全覆盖。
                # EN: Tree-sitter intentionally omits whitespace and may omit other
                # EN: unparsed bytes during recovery. Gaps are first-class trivia so
                # EN: the green tree still covers the source without holes.
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

    # 诊断和源码保真是两个独立维度：文件可以存在 parser error，
    # 但仍然必须做到逐字节 round-trip。
    # EN: Diagnostics are recorded separately from fidelity. A file may contain
    # EN: parser errors and still round-trip byte-for-byte.
    @staticmethod
    def _diagnostics(root: Node) -> list[Diagnostic]:
        """遍历 Tree-sitter CST，把 error/missing 节点转换为 xr-source 诊断。

        Traverse the Tree-sitter CST and convert error/missing nodes into xr-source diagnostics.
        """
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


# Runtime parser schema 故意比 LanguageGrammar 更小：它只描述已加载二进制
# 暴露了哪些 kind/field id，而不描述节点应如何组织。
# EN: Runtime parser schema is intentionally smaller than LanguageGrammar: it tells
# EN: us which kind/field ids the loaded binary exports, not how nodes are structured.
def _schema(language_name: str, language: Language) -> ParserSchema:
    """从 Tree-sitter Language 枚举 kind 与 field，构造 ParserSchema。

    Enumerate kinds and fields from a Tree-sitter Language and build a ParserSchema.
    """
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
    """读取 parser 返回的可选名称，并在异常缺失时抛出明确错误。

    Read an optional name returned by the parser and raise a clear error when it is
    unexpectedly absent.
    """
    if value is None:
        raise RuntimeError(f"Tree-sitter did not expose a name for {description}")
    return value


def _gap(data: bytes) -> GreenTrivia:
    """把 parser 未覆盖的原始源码字节区间转换为 GreenTrivia。

    Convert or adapt data for gap.
    """
    text = decode_source(data)
    if text.isspace():
        kind = "newline" if "\n" in text or "\r" in text else "whitespace"
    else:
        kind = "raw"
    return GreenTrivia(kind, text)
