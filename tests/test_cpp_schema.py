from xr_source.cpp import CppDocument, CppParser


def test_schema_exposes_modern_cpp_syntax_kinds() -> None:
    parser = CppParser()
    kinds = parser.schema.kind_names
    assert len(parser.schema.kinds) > 500
    assert {
        "lambda_expression",
        "requires_expression",
        "template_declaration",
        "concept_definition",
        "co_await_expression",
        "fold_expression",
    } <= kinds


def test_complex_cpp_syntax_remains_structured_and_lossless() -> None:
    source = b"""template <typename T>
concept Addable = requires(T t) { t + t; };

template <Addable T>
auto fold(T... xs) {
  auto lambda = []<typename U>(U value) requires Addable<U> { return value; };
  return (lambda(xs) + ...);
}
"""
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
    assert document.nodes("requires_expression")
    assert document.nodes("lambda_expression")
    assert document.nodes("fold_expression")


def test_utf8_bom_is_source_trivia_not_lost() -> None:
    source = b'\xef\xbb\xbf#pragma once\r\n'
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
