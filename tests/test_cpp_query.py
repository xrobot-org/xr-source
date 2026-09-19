"""验证 C++ 常用结构查询和 User Code 区域识别。
Test common C++ structure queries and User Code region detection.
"""
from xr_syntax.cpp import CppDocument

SOURCE = """
#include "foo.hpp"

class Device {
 public:
  Device(int value);
};

extern "C" void app_main(void) {
  static Device device(1);
  XR_REGISTER(device, Base);
  /* User Code Begin 3 */
  XROBOT_MAIN();
  /* User Code End 3 */
}
""".lstrip()


def test_common_queries() -> None:
    """验证 CppDocument 的常用函数、调用和声明查询。
    Verify the common CppDocument queries for functions, calls, and declarations.
    """
    document = CppDocument.parse(SOURCE)
    assert len(document.includes()) == 1
    assert len(document.classes("Device")) == 1
    assert len(document.functions("app_main")) == 1
    assert len(document.calls("XR_REGISTER")) == 1
    assert len(document.calls("XROBOT_MAIN")) == 1


def test_user_region() -> None:
    """验证 User Code 区域的名称、body 和边界识别。
    Verify User Code region names, bodies, and boundary detection.
    """
    document = CppDocument.parse(SOURCE)
    regions = document.user_regions()
    assert len(regions) == 1
    assert regions[0].name == "3"
    assert "XROBOT_MAIN();" in regions[0].body_text


def test_lexical_invocation_views_support_macro_type_lists() -> None:
    """验证宏式 invocation 能保留模板类型中的逗号并忽略注释/预处理定义。
    Verify lexical invocation queries preserve template commas and ignore comments/directives.
    """
    source = (
        "#define XR_REGISTER(name, ...) something(name, __VA_ARGS__)\n"
        "// XR_REGISTER(fake, Wrong)\n"
        "XR_REGISTER(array, std::array<int, 2>);\n"
        "XR_REGISTER(ref, Type&);\n"
    )
    document = CppDocument.parse(source)
    invocations = document.invocation_views("XR_REGISTER", template_angles=True)
    assert [(item.arguments, item.line) for item in invocations] == [
        (("array", "std::array<int, 2>"), 3),
        (("ref", "Type&"), 4),
    ]
