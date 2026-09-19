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
