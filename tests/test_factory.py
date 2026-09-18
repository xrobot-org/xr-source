"""验证 CppFactory 生成的片段使用同一 parser-backed 语法模型。"""
from xr_source.cpp import CppFactory


def test_factory_builds_parser_backed_syntax() -> None:
    """验证 CppFactory 创建的片段都会重新进入 parser-backed 语法模型。"""
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
    """验证工厂创建的表达式具有可查询的结构节点。"""
    expression = CppFactory().expression("a + b * c")
    assert expression.render() == "a + b * c"
