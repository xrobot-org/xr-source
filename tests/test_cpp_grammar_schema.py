"""验证原生 C++ grammar 合同、字段约束与 subtype 分类。
Test the native C++ grammar contract, field constraints, and subtype classification.
"""

from __future__ import annotations
from xr_syntax.cpp import CPP_GRAMMAR, CppParser


def test_cpp_grammar_schema_identity_and_root() -> None:
    """确认 C++ grammar 已由 xr-syntax 自己维护，而不是第三方 parser 元数据。
    Verify that the C++ grammar contract is owned by xr-syntax rather than third-party parser metadata.
    """
    assert CPP_GRAMMAR.version == "xr-cpp-0.1"
    assert CPP_GRAMMAR.source_revision == "native-source-model-v1"
    assert [(node.kind, node.named) for node in CPP_GRAMMAR.roots] == [("translation_unit", True)]


def test_expression_schema_covers_modern_cpp_expression_forms() -> None:
    """核心现代 C++ expression 分类必须继续暴露给上层查询。
    Verify that core modern C++ expression categories remain exposed to higher-level queries.
    """
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
    """binary expression 的 left/operator/right 合同必须稳定。
    Verify that the left/operator/right field contract for binary expressions remains stable.
    """
    binary = CPP_GRAMMAR.require_node("binary_expression", named=True)
    assert binary.field_names == ("left", "operator", "right")

    operator = binary.field("operator")
    assert operator is not None
    assert operator.required
    assert not operator.multiple
    operators = {(item.kind, item.named) for item in operator.types}
    assert {("+", False), ("<=>", False), ("and", False), ("||", False)} <= operators


def test_document_can_classify_nodes_through_grammar_schema() -> None:
    """解析出来的节点仍可通过自有 grammar subtype 图分类。
    Verify that parsed nodes can still be classified through the native grammar subtype graph.
    """
    from xr_syntax.cpp import CppDocument

    document = CppDocument.parse("void f() { if (ready) { target(a + b); } }")
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


def test_grammar_references_exist_in_native_parser_schema() -> None:
    """grammar 中声明的 kind 必须能被 native parser runtime schema 表达。
    Verify that every kind referenced by the grammar can be represented by the native parser runtime schema.
    """
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
