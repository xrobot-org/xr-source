from __future__ import annotations


def decode_source(data: bytes) -> str:
    return data.decode("utf-8", errors="surrogateescape")


def encode_source(text: str) -> bytes:
    return text.encode("utf-8", errors="surrogateescape")
