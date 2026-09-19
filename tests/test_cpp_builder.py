"""验证 C++ 文件、函数和代码块构建器覆盖常用生成场景。
Test common C++ file, function, and block generation workflows.
"""
from xr_syntax.cpp import CppFileBuilder


def test_source_builder_covers_common_generator_operations() -> None:
    """验证 C++ builder 覆盖常用代码生成操作。
    Verify that the C++ builder covers common source-generation operations.
    """
    source = CppFileBuilder()
    source.include("app_main.h")
    source.include("cstdint", system=True)
    source.variable("int", "global_counter", initializer="0", storage=["static"])

    app = source.function("void", "app_main", prefix=['extern "C"'])
    app.body.variable(
        "STM32GPIO",
        "LED_B",
        initializer="GPIOB",
        storage=["static"],
    )
    app.body.call("XR_REGISTER", ["LED_B", "LibXR::GPIO"])
    app.body.user_region(
        "3",
        [source.factory.call_statement("XROBOT_MAIN", [])],
    )

    document = source.build()
    text = document.render()
    assert '#include "app_main.h"' in text
    assert "#include <cstdint>" in text
    assert "static int global_counter = 0;" in text
    assert "static STM32GPIO LED_B = GPIOB;" in text
    assert "XR_REGISTER(LED_B, LibXR::GPIO);" in text
    assert "/* User Code Begin 3 */" in text
    assert len(document.functions("app_main")) == 1
    assert len(document.calls("XR_REGISTER")) == 1
    assert len(document.user_regions()) == 1


def test_header_builder_adds_pragma_once() -> None:
    """验证头文件 builder 会按约定加入 pragma once。
    Verify that the header builder emits pragma once as required.
    """
    header = CppFileBuilder(header=True)
    header.include("thread.hpp")
    document = header.build()
    assert document.render().startswith('#pragma once\n#include "thread.hpp"\n')


def test_file_builder_structures_format_and_lint_regions() -> None:
    """验证文件 builder 能生成结构化 format 与 lint 保护区域。
    Verify that the file builder creates structured format and lint protection regions.
    """
    source = CppFileBuilder()
    declaration = source.factory.declaration("static int generated = 0")
    source.format_disabled([declaration])
    source.lint_disabled([source.factory.call_statement("generated_call", [])])

    document = source.build()
    assert len(document.format_regions()) == 1
    assert len(document.lint_regions()) == 1
    assert "static int generated = 0;" in document.format_regions()[0].body_text
    assert "generated_call();" in document.lint_regions()[0].body_text
