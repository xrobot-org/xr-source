from __future__ import annotations

from xr_source.core import SyntaxElement, SyntaxNode, decode_source


def field_text(node: SyntaxNode, field: str) -> str | None:
    child = node.child_by_field(field)
    return None if child is None else child.text


def declaration_name_element(node: SyntaxNode) -> SyntaxElement | None:
    function = find_function_declarator(node)
    current = (
        function.child_by_field("declarator")
        if function is not None
        else node.child_by_field("declarator")
    )

    while isinstance(current, SyntaxNode):
        if current.kind in {"destructor_name", "operator_name"}:
            return current
        direct = current.child_by_field("declarator")
        if direct is not None:
            if isinstance(direct, SyntaxNode) and direct.kind in {
                "destructor_name",
                "operator_name",
            }:
                return direct
            current = direct
            continue
        for kind in (
            "identifier",
            "field_identifier",
            "type_identifier",
            "operator_name",
            "destructor_name",
        ):
            found = current.first_descendant(kind)
            if found is not None:
                return found
        break

    if current is not None:
        return current

    # Type template parameters such as 'typename T' have no declarator field.
    candidates = [
        child
        for child in node.named_syntax_children
        if child.kind in {"identifier", "type_identifier"}
    ]
    return candidates[-1] if candidates else None


def declaration_name(node: SyntaxNode) -> str | None:
    element = declaration_name_element(node)
    return None if element is None else element.text


def declarator_name_element(element: SyntaxElement) -> SyntaxElement | None:
    current: SyntaxElement | None = element
    while isinstance(current, SyntaxNode):
        if current.kind in {"destructor_name", "operator_name"}:
            return current
        direct = current.child_by_field("declarator")
        if direct is not None:
            current = direct
            continue
        for kind in (
            "identifier",
            "field_identifier",
            "type_identifier",
            "operator_name",
            "destructor_name",
        ):
            found = current.first_descendant(kind)
            if found is not None:
                return found
        return None
    if current is not None and current.kind in {
        "identifier",
        "field_identifier",
        "type_identifier",
        "operator_name",
        "destructor_name",
    }:
        return current
    return None


def declarator_name(element: SyntaxElement) -> str | None:
    name = declarator_name_element(element)
    return None if name is None else name.text


def declaration_type_text(node: SyntaxNode) -> str | None:
    name = declaration_name_element(node)
    if name is None:
        return None

    end = node.span.end
    equal = next(
        (child for child in node.syntax_children if child.kind == "="),
        None,
    )
    if equal is not None:
        end = equal.span.start

    source = node.tree.render_bytes()
    raw = (
        source[node.span.start : name.span.start]
        + source[name.span.end : end]
    )
    return decode_source(raw).strip()


def find_function_declarator(node: SyntaxNode) -> SyntaxNode | None:
    if node.kind == "function_declarator":
        return node
    found = node.first_descendant("function_declarator")
    return found if isinstance(found, SyntaxNode) else None


def named_elements(node: SyntaxNode, kinds: set[str]) -> tuple[SyntaxElement, ...]:
    return tuple(
        child
        for child in node.descendants()
        if child.kind in kinds
    )
