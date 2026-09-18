"""定义语言无关的 SyntaxDocument 外观，统一查询、不可变编辑和编辑后的重新解析。"""

from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar

from .diagnostic import Diagnostic
from .grammar import GrammarNodeSpec, LanguageGrammar
from .green import GreenElement
from .red import SyntaxElement, SyntaxNode, SyntaxToken
from .tree import SyntaxTree

# ---------------------------------------------------------------------------
# 语言无关的文档外观
# ---------------------------------------------------------------------------

class SyntaxParserProtocol(Protocol):
    """规定 SyntaxDocument 所需的最小解析器接口。"""
    def parse(
        self,
        source: str | bytes,
        *,
        source_name: str | None = None,
    ) -> SyntaxTree:
        """把源码文本或字节解析为一个不可变 SyntaxTree 快照。"""
        ...


DocumentT = TypeVar("DocumentT", bound="SyntaxDocument")


class SyntaxDocument:
    """表示某一语言的不可变文档快照；底层 SyntaxTree 编辑保留 green 共享，高层文档编辑会重新解析以刷新 field、诊断和语言不变量。"""
    __slots__ = ("tree", "_parser")

    language: str
    grammar: ClassVar[LanguageGrammar | None] = None

    def __init__(
        self,
        tree: SyntaxTree,
        parser: SyntaxParserProtocol,
    ) -> None:
        """绑定语法树、解析器和可选 grammar，形成一个不可变文档快照。"""
        if tree.language != self.language:
            raise ValueError(
                f"expected {self.language!r} syntax tree, got {tree.language!r}"
            )
        self.tree = tree
        self._parser = parser

    @property
    def root(self) -> SyntaxNode:
        """返回当前文档快照的 red 根节点。"""
        return self.tree.root

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """返回当前不可变快照在解析时产生的诊断。"""
        return self.tree.diagnostics

    def render(self) -> str:
        """按语法树中保存的源码内容原样渲染文本，不执行格式化。"""
        return self.tree.render()

    def render_bytes(self) -> bytes:
        """按原始编码规则渲染源码字节，并保留 surrogateescape 字节。"""
        return self.tree.render_bytes()

    def grammar_spec(self, element: SyntaxElement) -> GrammarNodeSpec | None:
        """把解析得到的元素映射回对应的版本化 grammar 结构合同。"""
        grammar = self.grammar
        if grammar is None or not isinstance(element, (SyntaxNode, SyntaxToken)):
            return None
        return grammar.node(element.kind, named=element.named)

    # 高层编辑刻意返回重新解析后的新快照。底层 tree API 可以保留 green 共享，
    # 但文档消费者在编辑后绝不能看到过期的 parser field 或诊断。
    def replace(
        self: DocumentT,
        target: SyntaxElement,
        replacement: SyntaxElement | GreenElement,
    ) -> DocumentT:
        """替换一个语法元素，重新解析结果并返回新的文档快照。"""
        return self._reparse(self.tree.replace(target, replacement).render_bytes())

    def remove(self: DocumentT, target: SyntaxElement) -> DocumentT:
        """删除一个语法元素，重新解析结果并返回新的文档快照。"""
        return self._reparse(self.tree.remove(target).render_bytes())

    def insert_before(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        """在目标元素前插入新元素，重新解析并返回新的文档快照。"""
        changed = self.tree.insert_before(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def insert_after(
        self: DocumentT,
        target: SyntaxElement,
        element: SyntaxElement | GreenElement,
        *,
        separator: str = "",
    ) -> DocumentT:
        """在目标元素后插入新元素，重新解析并返回新的文档快照。"""
        changed = self.tree.insert_after(target, element, separator=separator)
        return self._reparse(changed.render_bytes())

    def elements(self, kind: str) -> tuple[SyntaxElement, ...]:
        """返回匹配 kind 的全部语法元素，包括 named token 与 node。"""
        return tuple(self.root.descendants(kind, include_self=True))

    def nodes(self, kind: str) -> tuple[SyntaxNode, ...]:
        """只返回匹配 kind 的 SyntaxNode 节点。"""
        return tuple(
            element
            for element in self.elements(kind)
            if isinstance(element, SyntaxNode)
        )

    def _reparse(self: DocumentT, source: bytes) -> DocumentT:
        # 在语言文档边界统一重新解析，确保 field、诊断和错误恢复结构始终
        # 来源于真正拥有它们的 parser。以后可在不改变 API 的前提下做增量优化。
        """把底层编辑结果渲染为字节并重新解析，以刷新 field 和诊断。"""
        tree = self._parser.parse(source, source_name=self.tree.source_name)
        return type(self)(tree, self._parser)
