from xr_source.cpp import CPP_GRAMMAR, CppParser


def test_cpp_grammar_schema_identity_and_root() -> None:
    assert CPP_GRAMMAR.version == "0.23.4"
    assert CPP_GRAMMAR.source_revision == "f41e1a044c8a84ea9fa8577fdd2eab92ec96de02"
    assert len(CPP_GRAMMAR.nodes) == 407
    assert [(node.kind, node.named) for node in CPP_GRAMMAR.roots] == [
        ("translation_unit", True)
    ]


def test_expression_schema_covers_modern_cpp_expression_forms() -> None:
    expression = CPP_GRAMMAR.require_node("expression", named=True)
    subtypes = {(item.kind, item.named) for item in expression.subtypes}
    assert {
        ("binary_expression", True),
        ("call_expression", True),
        ("co_await_expression", True),
        ("fold_expression", True),
        ("lambda_expression", True),
        ("new_expression", True),
        ("requires_expression", True),
        ("user_defined_literal", True),
    } <= subtypes
    assert CPP_GRAMMAR.is_subtype("lambda_expression", "expression")
    assert CPP_GRAMMAR.is_subtype("fold_expression", "expression")
    assert not CPP_GRAMMAR.is_subtype("function_definition", "expression")


def test_binary_expression_field_contract_is_structured() -> None:
    binary = CPP_GRAMMAR.require_node("binary_expression", named=True)
    assert binary.field_names == ("left", "operator", "right")

    operator = binary.field("operator")
    assert operator is not None
    assert operator.required
    assert not operator.multiple
    operators = {(item.kind, item.named) for item in operator.types}
    assert {("+", False), ("<=>", False), ("and", False), ("||", False)} <= operators


def test_document_can_classify_nodes_through_grammar_schema() -> None:
    from xr_source.cpp import CppDocument

    document = CppDocument.parse(
        "void f() { if (ready) { target(a + b); } }"
    )
    binary = document.nodes("binary_expression")[0]
    call = document.nodes("call_expression")[0]
    compound = document.nodes("compound_statement")[0]

    assert document.is_expression(binary)
    assert document.is_expression(call)
    assert not document.is_expression(compound)
    assert document.is_statement(compound)

    spec = document.grammar_spec(binary)
    assert spec is not None
    assert spec.kind == "binary_expression"
    assert spec.field_names == ("left", "operator", "right")


def test_node_type_references_exist_in_runtime_grammar() -> None:
    runtime_kinds = CppParser().schema.kind_names
    missing: set[tuple[str, bool]] = set()

    for node in CPP_GRAMMAR.nodes:
        refs = list(node.subtypes)
        if node.children is not None:
            refs.extend(node.children.types)
        for _, field in node.fields:
            refs.extend(field.types)

        for ref in refs:
            if ref.kind not in runtime_kinds:
                missing.add((ref.kind, ref.named))

    assert not missing
