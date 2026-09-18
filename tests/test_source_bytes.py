"""验证包含非 UTF-8 字节的源码仍能无损解析和还原。"""
from xr_source.cpp import CppDocument


def test_non_utf8_bytes_still_roundtrip_losslessly() -> None:
    """验证包含非 UTF-8 字节的源码仍可通过 surrogateescape 无损 round-trip。"""
    source = b"int value; // byte: \xff\n"
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
