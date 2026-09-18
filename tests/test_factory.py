from xr_source.cpp import CppFactory


def test_factory_builds_parser_backed_syntax() -> None:
    factory = CppFactory(width=40)
    include = factory.include("libxr.hpp")
    call = factory.call_statement("XR_REGISTER", ["led", "LibXR::GPIO"])
    variable = factory.variable(
        "STM32GPIO",
        "led",
        storage=["static"],
        initializer="GPIOB",
    )

    assert include.render() == '#include "libxr.hpp"\n'
    assert "XR_REGISTER" in call.render()
    assert variable.render() == "static STM32GPIO led = GPIOB;"


def test_expression_is_structured() -> None:
    expression = CppFactory().expression("a + b * c")
    assert expression.render() == "a + b * c"
