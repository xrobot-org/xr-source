from xr_source.cpp import CppFileBuilder


def test_source_builder_covers_common_generator_operations() -> None:
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
    header = CppFileBuilder(header=True)
    header.include("thread.hpp")
    document = header.build()
    assert document.render().startswith('#pragma once\n#include "thread.hpp"\n')


def test_file_builder_structures_format_and_lint_regions() -> None:
    source = CppFileBuilder()
    declaration = source.factory.declaration("static int generated = 0")
    source.format_disabled([declaration])
    source.lint_disabled([source.factory.call_statement("generated_call", [])])

    document = source.build()
    assert len(document.format_regions()) == 1
    assert len(document.lint_regions()) == 1
    assert "static int generated = 0;" in document.format_regions()[0].body_text
    assert "generated_call();" in document.lint_regions()[0].body_text
