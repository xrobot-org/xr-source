"""xr-source 自有 C++ source grammar 合同。

这里描述的是 source parser 对外承诺的结构，不依赖 Tree-sitter 的 node-types.json。
它不是 C++ 类型系统，也不负责名字查找、重载决议或模板实例化。
"""

from __future__ import annotations

import hashlib

from xr_source.core import GrammarNodeSpec, GrammarSlot, GrammarTypeRef, LanguageGrammar

GRAMMAR_VERSION = "xr-cpp-0.1"
GRAMMAR_REVISION = "native-source-model-v1"


def _ref(kind: str, named: bool = True) -> GrammarTypeRef:
    """创建一个 grammar type 引用。"""
    return GrammarTypeRef(kind, named)


def _slot(*kinds: str, multiple: bool = False, required: bool = False, named: bool = True) -> GrammarSlot:
    """创建只包含同一 named 属性的一组 grammar slot 候选。"""
    return GrammarSlot(multiple, required, tuple(_ref(kind, named) for kind in kinds))


def _node(
    kind: str,
    *,
    named: bool = True,
    root: bool = False,
    fields: tuple[tuple[str, GrammarSlot], ...] = (),
    children: GrammarSlot | None = None,
    subtypes: tuple[GrammarTypeRef, ...] = (),
) -> GrammarNodeSpec:
    """创建一个 source grammar 节点说明。"""
    return GrammarNodeSpec(kind, named, root, fields, children, subtypes)


_EXPRESSION_KINDS = (
    "identifier",
    "number_literal",
    "string_literal",
    "char_literal",
    "raw_string_literal",
    "true",
    "false",
    "nullptr",
    "source_expression",
    "qualified_identifier",
    "parenthesized_expression",
    "unary_expression",
    "binary_expression",
    "assignment_expression",
    "conditional_expression",
    "call_expression",
    "field_expression",
    "subscript_expression",
    "lambda_expression",
    "requires_expression",
    "fold_expression",
    "new_expression",
    "delete_expression",
    "co_await_expression",
    "cast_expression",
    "initializer_list",
    "user_defined_literal",
)

_STATEMENT_KINDS = (
    "compound_statement",
    "expression_statement",
    "declaration_statement",
    "return_statement",
    "if_statement",
    "for_statement",
    "while_statement",
    "do_statement",
    "switch_statement",
    "break_statement",
    "continue_statement",
    "try_statement",
)

_DECLARATION_KINDS = (
    "declaration",
    "function_definition",
    "template_declaration",
    "namespace_definition",
    "class_specifier",
    "struct_specifier",
    "union_specifier",
    "enum_specifier",
    "concept_definition",
    "alias_declaration",
    "using_declaration",
)

_NODES = (
    _node(
        "translation_unit",
        root=True,
        children=_slot(*_DECLARATION_KINDS, "preproc_include", "preproc_def", "preproc_if", "preproc_ifdef", "preproc_call", "comment", multiple=True),
    ),
    _node("expression", subtypes=tuple(_ref(kind) for kind in _EXPRESSION_KINDS)),
    _node("statement", subtypes=tuple(_ref(kind) for kind in _STATEMENT_KINDS)),
    _node("declaration_item", subtypes=tuple(_ref(kind) for kind in _DECLARATION_KINDS)),
    *(_node(kind) for kind in (
        "identifier",
        "type_identifier",
        "field_identifier",
        "number_literal",
        "string_literal",
        "char_literal",
        "raw_string_literal",
        "true",
        "false",
        "nullptr",
        "source_expression",
        "qualified_identifier",
        "parenthesized_expression",
        "unary_expression",
        "conditional_expression",
        "field_expression",
        "subscript_expression",
        "lambda_expression",
        "requires_expression",
        "fold_expression",
        "new_expression",
        "delete_expression",
      "co_await_expression",
        "cast_expression",
        "initializer_list",
        "user_defined_literal",
        "expression_statement",
        "declaration_statement",
        "return_statement",
        "if_statement",
        "for_statement",
        "while_statement",
      "do_statement",
        "switch_statement",
        "break_statement",
        "continue_statement",
        "try_statement",
        "enum_specifier",
        "concept_definition",
        "alias_declaration",
        "using_declaration",
        "type_descriptor",
        "pointer_declarator",
      "reference_declarator",
      "array_declarator",
        "parenthesized_declarator",
        "destructor_name",
        "operator_name",
        "default_method_clause",
      "delete_method_clause",
      "preproc_def",
      "preproc_if",
        "preproc_ifdef",
      "preproc_call",
        "comment",
        "storage_class_specifier",
        "type_qualifier",
      "system_lib_string",
      "access_specifier",
    )),

    _node(
        "compound_statement",
        fields=(("body", _slot(*_STATEMENT_KINDS, multiple=True)),
        children=_slot(*_STATEMENT_KINDS, "declaration", "comment", multiple=True),
    ),
    _node(
        "binary_expression",
        fields=(
            ("left", _slot(*_EXPRESSION_KINDS, required=True)),
            ("operator", GrammarSlot(False, True, tuple(_ref(item, False) for item in (
                "+", "-", "*", "/", "%", "<<", ">>", "<", "<=", ">", ">=", "==", "!=", "<=>", "&", "^", "|", "&&", "||", "and", "or", "xor"
            )))),
            ("right", _slot(*_EXPRESSION_KINDS, required=True)),
        ),
    ),
    _node(
        "assignment_expression",
        fields=(
            ("left", _slot(*_EXPRESSION_KINDS, required=True)),
            ("operator", GrammarSlot(False, True, tuple(_ref(item, False) for item in ("=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=")))),
            ("right", _slot(*_EXPRESSION_KINDS, required=True)),
       ),
    ),
    _node(
        "call_expression",
        fields=(
            ("function", _slot(*_EXPRESSION_KINDS, required=True)),
            ("arguments", _slot("argument_list", required=True)),
        ),
    ),
    _node("argument_list", children=_slot(*_EXPRESSION_KINDS, multiple=True)),
    _node(
        "function_definition",
        fields=(
            ("type", _slot("type_descriptor")),
            ("declarator", _slot("function_declarator", required=True)),
            ("body", _slot("compound_statement", required=True)),
       ),
    ),
    _node(
        "function_declarator",
        fields=(
            ("declarator", _slot("identifier", "operator_name", "destructor_name", required=True)),
            ("parameters", _slot("parameter_list", required=True)),
         ),
    ),
    _node("parameter_list", children=_slot("parameter_declaration", "optional_parameter_declaration", multiple=True)),
    _node(
        "parameter_declaration",
        fields=(
            ("declarator", _slot("identifier", "type_identifier")),
            ("default_value", _slot(*_EXPRESSION_KINDS)),
        ),
    ),
    _node(
        "optional_parameter_declaration",
        fields=(
            ("declarator", _slot("identifier", "type_identifier")),
            ("default_value", _slot(*_EXPRESSION_KINDS, required=True)),
       ),
    ),
    _node(
        "declaration",
        fields=(
            ("type", _slot("type_descriptor")),
            ("declarator", _slot("init_declarator", "function_declarator", multiple=True)),
        ),
    ),
    _node(
        "init_declarator",
        fields=(
            ("declarator", _slot("identifier", "type_identifier", required=True)),
            ("value", _slot(*_EXPRESSION_KINDS)),
       ),
    ),
    _node(
        "template_declaration",
        fields=(("parameters", _slot("template_parameter_list", required=True)),),
        children=_slot(*_DECLARATION_KINDS, multiple=True),
    ),
    _node("template_parameter_list", children=_slot("type_parameter_declaration", "optional_type_parameter_declaration", "parameter_declaration", "optional_parameter_declaration", "variadic_parameter_declaration", multiple=True)),
    _node("type_parameter_declaration", fields=(("declarator", _slot("type_identifier", "identifier")),)),
    _node("optional_type_parameter_declaration", fields=(("declarator", _slot("type_identifier", "identifier")), ("default_type", _slot(*_EXPRESSION_KINDS)))),
    _node("variadic_parameter_declaration", fields=(("declarator", _slot("type_identifier", "identifier")),)),
    *(
        _node(
            kind,
            fields=(
                ("name", _slot("type_identifier", "identifier")),
                ("body", _slot("field_declaration_list")),
            ),
        )
        for kind in ("class_specifier", "struct_specifier", "union_specifier")
    ),
    _node("field_declaration_list", children=_slot("access_specifier", "declaration", "function_definition", "template_declaration", "class_specifier", "struct_specifier", "union_specifier", "comment", multiple=True)),
    _node("namespace_definition", fields=(("name", _slot("identifier")), ("body", _slot("declaration_list", required=True)))),
    _node("declaration_list", children=_slot(*_DECLARATION_KINDS, "comment", multiple=True)),
    _node("preproc_include", fields=(("path", _slot("string_literal", "system_lib_string", required=True)),)),
)

# Grammar identity 基二本文件内置合同， # 不是第三料 grammar revision。
_SCHEMA_FINGERPRINT = "\n".join(
    "{}:{}:{}".format(node.kind, int(node.named), ",".join(node.field_names))
    for node in _NODES
).encode("utf-8")
NODE_TYPES_SHA256 = hashlib.sha256(_SCHEMA_FINGERPRINT).hexdigest()

CPP_GRAMMAR = LanguageGrammar(
    language="cpp",
    version=GRAMMAR_VERSION,
    source_revision=GRAMMAR_REVISION,
    source_sha256=NODE_TYPES_SHA256,
    nodes=tuple(_NODES),
)

__all__ = [
    "CPP_GRAMMAR",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
    "NODE_TYPES_SHA256",
]
