from xr_source.cpp import CppDocument


def test_non_utf8_bytes_still_roundtrip_losslessly() -> None:
    source = b"int value; // byte: \xff\n"
    document = CppDocument.parse(source)
    assert document.render_bytes() == source
