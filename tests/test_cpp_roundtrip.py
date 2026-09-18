"""验证原生 C++ parser 的逐字节 round-trip 不变量及关键回归场景。"""
from xr_source.cpp import CppDocument


def test_roundtrip_preserves_every_byte() -> None:
    """验证 C++ parse/render 对输入源码保持逐字节一致。"""
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
    """验证空 translation unit 仍能无损表示且没有诊断。"""
    document = CppDocument.parse(b"")
    assert document.render_bytes() == b""
    assert document.root.kind == "translation_unit"
    assert not document.diagnostics


def test_incomplete_source_is_still_lossless() -> None:
    """验证不完整 C++ 源码即使产生诊断也仍能逐字节还原。"""
    source = b"void f() {\n  foo(\n"
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
    assert document.diagnostics


def test_expression_replacements_preserve_edge_trivia() -> None:
    """验证表达式结构 replacement 不会吞掉边缘空白、换行或预处理 trivia。"""
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
