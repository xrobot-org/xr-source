from xr_source.cpp import CppDocument

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
    document = CppDocument.parse(SOURCE)
    assert len(document.includes()) == 1
    assert len(document.classes("Device")) == 1
    assert len(document.functions("app_main")) == 1
    assert len(document.calls("XR_REGISTER")) == 1
    assert len(document.calls("XROBOT_MAIN")) == 1


def test_user_region() -> None:
    document = CppDocument.parse(SOURCE)
    regions = document.user_regions()
    assert len(regions) == 1
    assert regions[0].name == "3"
    assert "XROBOT_MAIN();" in regions[0].body_text
