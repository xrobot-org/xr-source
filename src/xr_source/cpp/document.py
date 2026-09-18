"""提供 C++ 高层查询、类型化视图入口以及受保护源码区域的编辑能力。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from xr_source.core import (
    SourceSpan,
    SyntaxDocument,
    SyntaxElement,
    SyntaxNode,
    SyntaxToken,
    encode_source,
)

from .grammar import CPP_GRAMMAR
from .parser import CppParser
from .syntax_utils import declaration_name, field_text
from .view import (
    CppCallView,
    CppClassView,
    CppFunctionView,
    CppIncludeView,
    CppVariableView,
)

# ---------------------------------------------------------------------------
# 受保护源码区域
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CppRegion:
    """表示由成对标记界定的源码保护区域，例如 User Code、clang-format 或 NOLINT。"""
    kind: str
    name: str | None
    begin: SyntaxElement
    end: SyntaxElement
    body_span: SourceSpan
    body_text: str


# ---------------------------------------------------------------------------
# C++ 文档查询
# ---------------------------------------------------------------------------

class CppDocument(SyntaxDocument):
    """在完整 C++ 语法树之上提供高层文档能力。\n\n    包括源码级查询、保护区编辑和类型化视图入口；只处理语法结构，\n    不做名称查找、重载决议或类型推导。\n    """
    __slots__ = ()

    language = "cpp"
    grammar = CPP_GRAMMAR

    @classmethod
    def parse(
        cls,
        source: str | bytes,
        *,
        source_name: str | None = None,
        parser: CppParser | None = None,
    ) -> CppDocument:
        """使用 xr-source 原生 C++ parser 解析源码并保留 source_name。"""
        selected = parser or CppParser()
        return cls(
            selected.parse(source, source_name=source_name),
            selected,
        )

    def is_expression(self, element: SyntaxElement) -> bool:
        """依据 C++ grammar subtype 图判断元素是否属于 expression。"""
        if not isinstance(element, (SyntaxNode, SyntaxToken)):
            return False
        return self.grammar.is_subtype(
            element.kind,
            "expression",
            actual_named=element.named,
        )

    def is_statement(self, element: SyntaxElement) -> bool:
        """依据 C++ grammar subtype 图判断元素是否属于 statement。"""
        if not isinstance(element, (SyntaxNode, SyntaxToken)):
            return False
        return self.grammar.is_subtype(
            element.kind,
            "statement",
            actual_named=element.named,
        )

    def replace_region_body(self, region: CppRegion, body: str) -> CppDocument:
        """只替换成对区域标记之间的源码字节，并重新解析整个文档。"""
        source = self.render_bytes()
        replacement = encode_source(body)
        changed = (
            source[: region.body_span.start]
            + replacement
            + source[region.body_span.end :]
        )
        return self._reparse(changed)

    def includes(self) -> tuple[SyntaxNode, ...]:
        """按源码顺序返回原始 preproc_include 节点。"""
        return self.nodes("preproc_include")

    def include_views(self) -> tuple[CppIncludeView, ...]:
        """为全部 include 节点创建 CppIncludeView。"""
        return tuple(CppIncludeView(node) for node in self.includes())

    def comments(self) -> tuple[SyntaxElement, ...]:
        """按源码顺序返回 parser 识别的注释元素。"""
        return self.elements("comment")

    def functions(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        """返回函数定义，并可按源码级函数名过滤。"""
        nodes = self.nodes("function_definition")
        if name is None:
            return nodes
        return tuple(node for node in nodes if declaration_name(node) == name)

    def classes(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        """返回 class/struct 定义，并可按源码级名称过滤。"""
        nodes = self.nodes("class_specifier") + self.nodes("struct_specifier")
        if name is None:
            return nodes
        return tuple(node for node in nodes if field_text(node, "name") == name)

    def calls(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        """返回调用表达式，并可按精确 callee 源码文本过滤。"""
        nodes = self.nodes("call_expression")
        if name is None:
            return nodes
        return tuple(node for node in nodes if field_text(node, "function") == name)

    def function_views(self, name: str | None = None) -> tuple[CppFunctionView, ...]:
        """把匹配的函数节点包装为 CppFunctionView。"""
        return tuple(CppFunctionView(node) for node in self.functions(name))

    def class_views(self, name: str | None = None) -> tuple[CppClassView, ...]:
        """把匹配的类节点包装为 CppClassView。"""
        return tuple(CppClassView(node) for node in self.classes(name))

    def call_views(self, name: str | None = None) -> tuple[CppCallView, ...]:
        """把匹配的调用节点包装为 CppCallView。"""
        return tuple(CppCallView(node) for node in self.calls(name))

    # 多种声明形式会落到同一个通用 declaration node。这里仅筛选明显的
    # 变量 declarator，不试图复刻编译器完整的声明语义。
    def variable_views(
        self,
        name: str | None = None,
        *,
        global_scope: bool | None = None,
    ) -> tuple[CppVariableView, ...]:
        """返回变量声明视图，并可按全局/局部作用域过滤。"""
        result: list[CppVariableView] = []
        for declaration in self.nodes("declaration"):
            for declarator in declaration.children_by_field("declarator"):
                if isinstance(declarator, SyntaxNode) and (
                    declarator.kind == "function_declarator"
                    or declarator.first_descendant("function_declarator") is not None
                ):
                    continue
                view = CppVariableView(declaration, declarator)
                if name is not None and view.name != name:
                    continue
                if global_scope is not None and view.global_scope != global_scope:
                    continue
                result.append(view)
        return tuple(result)

    def declarations(self) -> tuple[SyntaxNode, ...]:
        """返回文档中的声明节点集合。"""
        kinds = ("declaration", "function_definition", "template_declaration")
        return tuple(node for kind in kinds for node in self.nodes(kind))

    def user_regions(self) -> tuple[CppRegion, ...]:
        """识别并返回成对的 User Code Begin/End 区域。"""
        return self._paired_comment_regions(
            kind="user",
            begin=re.compile(r"/\*\s*User Code Begin(?:\s+(.+?))?\s*\*/"),
            end=re.compile(r"/\*\s*User Code End(?:\s+(.+?))?\s*\*/"),
        )

    def format_regions(self) -> tuple[CppRegion, ...]:
        """识别并返回 clang-format off/on 区域。"""
        return self._paired_comment_regions(
            kind="format",
            begin=re.compile(r"//\s*clang-format\s+off\b"),
            end=re.compile(r"//\s*clang-format\s+on\b"),
        )

    def lint_regions(self) -> tuple[CppRegion, ...]:
        """识别并返回 NOLINTBEGIN/NOLINTEND 区域。"""
        return self._paired_comment_regions(
            kind="lint",
            begin=re.compile(r"//\s*NOLINTBEGIN\b"),
            end=re.compile(r"//\s*NOLINTEND\b"),
        )

    # 区域配对只是建立在普通 C++ 注释之上的源码约定，因此刻意放在 grammar
    # 之上实现，而不是为了这个约定去污染 parser。
    def _paired_comment_regions(
        self,
        *,
        kind: str,
        begin: re.Pattern[str],
        end: re.Pattern[str],
    ) -> tuple[CppRegion, ...]:
        """按 begin/end 正则匹配成对注释，并构造带 body span 的区域对象。"""
        source = self.render_bytes()
        stack: list[tuple[SyntaxElement, str | None]] = []
        regions: list[CppRegion] = []
        for comment in sorted(self.comments(), key=lambda node: node.span.start):
            begin_match = begin.fullmatch(comment.text.strip())
            if begin_match:
                name = begin_match.group(1).strip() if begin_match.lastindex else None
                stack.append((comment, name))
                continue
            end_match = end.fullmatch(comment.text.strip())
            if not end_match or not stack:
                continue
            start, name = stack.pop()
            if end_match.lastindex and name is not None:
                end_name = end_match.group(1).strip()
                if end_name != name:
                    continue
            body = SourceSpan(start.span.end, comment.span.start)
            regions.append(
                CppRegion(
                    kind,
                    name,
                    start,
                    comment,
                    body,
                    source[body.start : body.end].decode(
                        "utf-8",
                        errors="surrogateescape",
                    ),
                )
            )
        return tuple(regions)
