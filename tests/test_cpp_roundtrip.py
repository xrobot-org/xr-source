from xr_source.cpp import CppDocument


def test_roundtrip_preserves_every_byte() -> None:
    source = (
        b'#include "foo.hpp"\r\n'
        b"\r\n"
        b"// comment\r\n"
        b"#define FOO(x) ((x) + 1)\r\n"
        b"template <typename T>\r\n"
        b"T f(T value) {\r\n"
        b'  auto s = R"tag(a // b)tag";\r\n'
        b"  return FOO(value);\r\n"
        b"}\r\n"
    )
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
    assert not document.diagnostics


def test_empty_translation_unit_is_a_lossless_node() -> None:
    document = CppDocument.parse(b"")
    assert document.render_bytes() == b""
    assert document.root.kind == "translation_unit"
    assert not document.diagnostics


def test_incomplete_source_is_still_lossless() -> None:
    source = b"void f() {\n  foo(\n"
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
    assert document.diagnostics


def test_expression_replacements_preserve_edge_trivia() -> None:
    source = (
        b"bool f(bool ready) {\n"
        b"  return ready\n"
        b"#if defined(EXTRA)\n"
        b"         && extra\n"
        b"#endif\n"
        b"      ;\n"
        b"}\n"
        b"enum { Options = Options_ };\n"
        b"void g() { int value = 1 ; target((value   )); }\n"
    )
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
