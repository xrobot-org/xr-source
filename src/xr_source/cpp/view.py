"""Convenience views for common C++ source constructs without replacing the full syntax tree."""

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

# ---------------------------------------------------------------------------
# Typed convenience views over the complete C++ syntax tree
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CppIncludeView:
    """Convenience view of one C++ preprocessor include directive."""
    node: SyntaxNode

    @property
    def path(self) -> str | None:
        """Return the source spelling of this path."""
        value = self.node.child_by_field("path")
        return None if value is None else value.text

    @property
    def header(self) -> str | None:
        """Return the include header name without delimiters."""
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
        """Report whether this include uses angle-bracket system syntax."""
        path = self.path
        return bool(path and path.startswith("<") and path.endswith(">"))


@dataclass(frozen=True, slots=True)
class CppVariableView:
    """Source-structural view of one declarator inside a C++ declaration."""
    node: SyntaxNode
    declarator: SyntaxElement

    @property
    def name(self) -> str | None:
        """Return the source-level name when available."""
        return declarator_name(self.declarator)

    @property
    def base_type(self) -> str | None:
        """Return parser type-field text before declarator wrappers."""
        return field_text(self.node, "type")

    @property
    def storage(self) -> tuple[str, ...]:
        """Return source storage-class specifiers."""
        return tuple(
            child.text.strip()
            for child in self.node.syntax_children
            if child.kind == "storage_class_specifier"
        )

    @property
    def qualifiers(self) -> tuple[str, ...]:
        """Return source type qualifiers."""
        return tuple(
            child.text.strip()
            for child in self.node.syntax_children
            if child.kind == "type_qualifier"
        )

    @property
    def initializer(self) -> str | None:
        """Return initializer source text when present."""
        if not isinstance(self.declarator, SyntaxNode):
            return None
        value = self.declarator.child_by_field("value")
        return None if value is None else value.text.strip()

    @property
    def global_scope(self) -> bool:
        """Report whether this declaration is outside every compound statement."""
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
    """Convenience view exposing a function parameter's source name/type/default text."""
    node: SyntaxNode

    @property
    def text(self) -> str:
        """Wrap literal text as a layout document."""
        return self.node.text

    @property
    def name(self) -> str | None:
        """Return the source-level name when available."""
        return declaration_name(self.node)

    @property
    def type(self) -> str | None:
        """Return reconstructed source-level type text."""
        return declaration_type_text(self.node)

    @property
    def default(self) -> str | None:
        """Return default source text when present."""
        value = self.node.child_by_field("default_value")
        if value is None:
            value = self.node.child_by_field("value")
        return None if value is None else value.text.strip()


@dataclass(frozen=True, slots=True)
class CppTemplateParameterView:
    """Convenience view exposing a template parameter's source components."""
    node: SyntaxNode

    @property
    def text(self) -> str:
        """Wrap literal text as a layout document."""
        return self.node.text

    @property
    def name(self) -> str | None:
        """Return the source-level name when available."""
        return declaration_name(self.node)

    @property
    def type(self) -> str | None:
        """Return reconstructed source-level type text."""
        return declaration_type_text(self.node)

    @property
    def default(self) -> str | None:
        """Return default source text when present."""
        value = self.node.child_by_field("default_value")
        if value is None:
            value = self.node.child_by_field("default_type")
        return None if value is None else value.text.strip()


@dataclass(frozen=True, slots=True)
class CppFunctionView:
    """Source-structural function/method view with parameter and special-member helpers."""
    node: SyntaxNode
    access: str | None = None

    @property
    def name(self) -> str | None:
        """Return the source-level name when available."""
        return declaration_name(self.node)

    @property
    def declarator(self) -> SyntaxNode | None:
        """Return the function declarator carrying parameters and qualifiers."""
        return find_function_declarator(self.node)

    @property
    def parameters(self) -> tuple[CppParameterView, ...]:
        """Return typed views of declared parameters."""
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
        """Return the parsed body element when present."""
        return self.node.child_by_field("body")

    @property
    def deleted(self) -> bool:
        """Report whether this member is syntactically declared '= delete'."""
        return self.node.first_descendant("delete_method_clause") is not None

    @property
    def defaulted(self) -> bool:
        """Report whether this member is syntactically declared '= default'."""
        return self.node.first_descendant("default_method_clause") is not None


@dataclass(frozen=True, slots=True)
class CppCallView:
    """Convenience view of a call expression and its argument syntax elements."""
    node: SyntaxNode

    @property
    def callee(self) -> str | None:
        """Return exact source text for the called expression."""
        return field_text(self.node, "function")

    @property
    def arguments(self) -> tuple[SyntaxElement, ...]:
        """Return argument syntax elements in source order."""
        arguments = self.node.child_by_field("arguments")
        if not isinstance(arguments, SyntaxNode):
            return ()
        return arguments.named_syntax_children


# Class/member convenience helpers stop at source structure. They do not resolve
# inherited constructors, overload viability, or compiler type conversions.
@dataclass(frozen=True, slots=True)
class CppClassView:
    """Convenience class/struct view that tracks C++ access sections while scanning members."""
    node: SyntaxNode

    @property
    def name(self) -> str | None:
        """Return the source-level name when available."""
        return field_text(self.node, "name")

    @property
    def default_access(self) -> str:
        """Return the C++ default member access for class versus struct."""
        return "public" if self.node.kind == "struct_specifier" else "private"

    @property
    def body(self) -> SyntaxNode | None:
        """Return the parsed body element when present."""
        body = self.node.child_by_field("body")
        return body if isinstance(body, SyntaxNode) else None

    def functions(self) -> tuple[CppFunctionView, ...]:
        """Return syntactically declared member functions with effective access labels."""
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
        """Return parameters when the class is directly wrapped by a template declaration."""
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
        """Return constructor declarations for this class.

        public_only filters by syntactic access. callable_only removes = delete members
        but deliberately keeps = default constructors because they remain callable.
        """
        name = self.name
        result = tuple(function for function in self.functions() if function.name == name)
        if public_only:
            result = tuple(function for function in result if function.access == "public")
        if callable_only:
            result = tuple(function for function in result if not function.deleted)
        return result
