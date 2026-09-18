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


@dataclass(frozen=True, slots=True)
class CppRegion:
    kind: str
    name: str | None
    begin: SyntaxElement
    end: SyntaxElement
    body_span: SourceSpan
    body_text: str


class CppDocument(SyntaxDocument):
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
        selected = parser or CppParser()
        return cls(
            selected.parse(source, source_name=source_name),
            selected,
        )

    def is_expression(self, element: SyntaxElement) -> bool:
        if not isinstance(element, (SyntaxNode, SyntaxToken)):
            return False
        return self.grammar.is_subtype(
            element.kind,
            "expression",
            actual_named=element.named,
        )

    def is_statement(self, element: SyntaxElement) -> bool:
        if not isinstance(element, (SyntaxNode, SyntaxToken)):
            return False
        return self.grammar.is_subtype(
            element.kind,
            "statement",
            actual_named=element.named,
        )

    def replace_region_body(self, region: CppRegion, body: str) -> CppDocument:
        source = self.render_bytes()
        replacement = encode_source(body)
        changed = (
            source[: region.body_span.start]
            + replacement
            + source[region.body_span.end :]
        )
        return self._reparse(changed)

    def includes(self) -> tuple[SyntaxNode, ...]:
        return self.nodes("preproc_include")

    def include_views(self) -> tuple[CppIncludeView, ...]:
        return tuple(CppIncludeView(node) for node in self.includes())

    def comments(self) -> tuple[SyntaxElement, ...]:
        return self.elements("comment")

    def functions(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        nodes = self.nodes("function_definition")
        if name is None:
            return nodes
        return tuple(node for node in nodes if declaration_name(node) == name)

    def classes(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        nodes = self.nodes("class_specifier") + self.nodes("struct_specifier")
        if name is None:
            return nodes
        return tuple(node for node in nodes if field_text(node, "name") == name)

    def calls(self, name: str | None = None) -> tuple[SyntaxNode, ...]:
        nodes = self.nodes("call_expression")
        if name is None:
            return nodes
        return tuple(node for node in nodes if field_text(node, "function") == name)

    def function_views(self, name: str | None = None) -> tuple[CppFunctionView, ...]:
        return tuple(CppFunctionView(node) for node in self.functions(name))

    def class_views(self, name: str | None = None) -> tuple[CppClassView, ...]:
        return tuple(CppClassView(node) for node in self.classes(name))

    def call_views(self, name: str | None = None) -> tuple[CppCallView, ...]:
        return tuple(CppCallView(node) for node in self.calls(name))

    def variable_views(
        self,
        name: str | None = None,
        *,
        global_scope: bool | None = None,
    ) -> tuple[CppVariableView, ...]:
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
        kinds = ("declaration", "function_definition", "template_declaration")
        return tuple(node for kind in kinds for node in self.nodes(kind))

    def user_regions(self) -> tuple[CppRegion, ...]:
        return self._paired_comment_regions(
            kind="user",
            begin=re.compile(r"/\*\s*User Code Begin(?:\s+(.+?))?\s*\*/"),
            end=re.compile(r"/\*\s*User Code End(?:\s+(.+?))?\s*\*/"),
        )

    def format_regions(self) -> tuple[CppRegion, ...]:
        return self._paired_comment_regions(
            kind="format",
            begin=re.compile(r"//\s*clang-format\s+off\b"),
            end=re.compile(r"//\s*clang-format\s+on\b"),
        )

    def lint_regions(self) -> tuple[CppRegion, ...]:
        return self._paired_comment_regions(
            kind="lint",
            begin=re.compile(r"//\s*NOLINTBEGIN\b"),
            end=re.compile(r"//\s*NOLINTEND\b"),
        )

    def _paired_comment_regions(
        self,
        *,
        kind: str,
        begin: re.Pattern[str],
        end: re.Pattern[str],
    ) -> tuple[CppRegion, ...]:
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
