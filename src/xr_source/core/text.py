"""Lossless conversion between source bytes and Python text using surrogate escapes."""

from __future__ import annotations


def decode_source(data: bytes) -> str:
    """Decode source bytes with surrogateescape so undecodable bytes can round-trip unchanged."""
    return data.decode("utf-8", errors="surrogateescape")


def encode_source(text: str) -> bytes:
    """Encode source text with surrogateescape, reversing decode_source for preserved bytes."""
    return text.encode("utf-8", errors="surrogateescape")
