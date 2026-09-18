from __future__ import annotations

from dataclasses import dataclass

from xr_source.core import SyntaxElement, SyntaxNode

from .syntax_utils import (
    declaration_name,
    declaration_type_text,
    declarator_name,
    field_text,
    find_function_declarator,
)


@dataclass(frozen=True, slots=True)
class CppIncludeView:
    node: SyntaxNode

    @property
    def path(self) -> str | None:
        value = self.node.child_by_field("path")
        return None if value is None else value.text

    @property
    def header(self) -> str | None:
        path = self.path
        if path is None:
            return None
        if (
            len(path) >= 2
            and (path[0], path[-1]) in {('"', '"'), ("<", ">")}
        ):
            return path[1:-1]
        return path

    @property
    def system(self) -> bool:
        path = self.path
        return bool(path and path.startswith("<") and path.endswith(">"))


@dataclass(frozen=True, slots=True)
class CppVariableView:
    node: SyntaxNode
    declarator: SyntaxElement

    @property
    def name(self) -> str | None:
        return declarator_name(self.declarator)

    @property
    def base_type(self) -> str | None:
        return field_text(self.node, "type")

    @property
    def storage(self) -> tuple[str, ...]:
        return tuple(
            child.text.strip()
            for child in self.node.syntax_children
            if child.kind == "storage_class_specifier"
        )

    @property
    def qualifiers(self) -> tuple[str, ...]:
        return tuple(
            child.text.strip()
            for child in self.node.syntax_children
            if child.kind == "type_qualifier"
        )

    @property
    def initializer(self) -> str | None:
        if not isinstance(self.declarator, SyntaxNode):
            return None
        value = self.declarator.child_by_field("value")
        return None if value is None else value.text.strip()

    @property
    def global_scope(self) -> bool:
        parent = self.node.parent
        while parent is not None:
            if parent.kind == "compound_statement":
                return False
            if parent.kind == "translation_unit":
                return True
            parent = parent.parent
        return False


@dataclass(frozen=True, slots=True)
class CppParameterView:
    node: SyntaxNode

    @property
    def text(self) -> str:
        return self.node.text

    @property
    def name(self) -> str | None:
        return declaration_name(self.node)

    @property
    def type(self) -> str | None:
        return declaration_type_text(self.node)

    @property
    def default(self) -> str | None:
        value = self.node.child_by_field("default_value")
        if value is None:
            value = self.node.child_by_field("value")
        return None if value is None else value.text.strip()


@dataclass(frozen=True, slots=True)
class CppTemplateParameterView:
    node: SyntaxNode

    @property
    def text(self) -> str:
        return self.node.text

    @property
    def name(self) -> str | None:
        return declaration_name(self.node)

    @property
    def type(self) -> str | None:
        return declaration_type_text(self.node)

    @property
    def default(self) -> str | None:
        value = self.node.child_by_field("default_value")
        if value is None:
            value = self.node.child_by_field("default_type")
        return None if value is None else value.text.strip()


@dataclass(frozen=True, slots=True)
class CppFunctionView:
    node: SyntaxNode
    access: str | None = None

    @property
    def name(self) -> str | None:
        return declaration_name(self.node)

    @property
    def declarator(self) -> SyntaxNode | None:
        return find_function_declarator(self.node)

    @property
    def parameters(self) -> tuple[CppParameterView, ...]:
        declarator = self.declarator
        if declarator is None:
            return ()
        parameters = declarator.child_by_field("parameters")
        if not isinstance(parameters, SyntaxNode):
            return ()
        return tuple(
            CppParameterView(child)
            for child in parameters.named_children
            if child.kind in {"parameter_declaration", "optional_parameter_declaration"}
        )

    @property
    def body(self) -> SyntaxElement | None:
        return self.node.child_by_field("body")

    @property
    def deleted(self) -> bool:
        return self.node.first_descendant("delete_method_clause") is not None

    @property
    def defaulted(self) -> bool:
        return self.node.first_descendant("default_method_clause") is not None


@dataclass(frozen=True, slots=True)
class CppCallView:
    node: SyntaxNode

    @property
    def callee(self) -> str | None:
        return field_text(self.node, "function")

    @property
    def arguments(self) -> tuple[SyntaxElement, ...]:
        arguments = self.node.child_by_field("arguments")
        if not isinstance(arguments, SyntaxNode):
            return ()
        return arguments.named_syntax_children


@dataclass(frozen=True, slots=True)
class CppClassView:
    node: SyntaxNode

    @property
    def name(self) -> str | None:
        return field_text(self.node, "name")

    @property
    def default_access(self) -> str:
        return "public" if self.node.kind == "struct_specifier" else "private"

    @property
    def body(self) -> SyntaxNode | None:
        body = self.node.child_by_field("body")
        return body if isinstance(body, SyntaxNode) else None

    def functions(self) -> tuple[CppFunctionView, ...]:
        body = self.body
        if body is None:
            return ()
        access = self.default_access
        result: list[CppFunctionView] = []
        for child in body.named_children:
            if child.kind == "access_specifier":
                access = child.text.strip().rstrip(":")
                continue
            if find_function_declarator(child) is not None:
                result.append(CppFunctionView(child, access))
        return tuple(result)

    @property
    def template_parameters(self) -> tuple[CppTemplateParameterView, ...]:
        parent = self.node.parent
        if parent is None or parent.kind != "template_declaration":
            return ()
        parameters = parent.child_by_field("parameters")
        if not isinstance(parameters, SyntaxNode):
            return ()
        return tuple(
            CppTemplateParameterView(child)
            for child in parameters.named_children
            if child.kind
            in {
                "type_parameter_declaration",
                "optional_type_parameter_declaration",
                "parameter_declaration",
                "optional_parameter_declaration",
                "variadic_parameter_declaration",
            }
        )

    def constructors(
        self,
        *,
        public_only: bool = False,
        callable_only: bool = False,
    ) -> tuple[CppFunctionView, ...]:
        name = self.name
        result = tuple(function for function in self.functions() if function.name == name)
        if public_only:
            result = tuple(function for function in result if function.access == "public")
        if callable_only:
            result = tuple(function for function in result if not function.deleted)
        return result
