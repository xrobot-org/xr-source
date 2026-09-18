"""Checksummed CMake grammar metadata pinned to the language-pack upstream revision."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import Any

from xr_source.core import LanguageGrammar

GRAMMAR_VERSION = "0.7.4"
GRAMMAR_REVISION = "ca627bb5828616b6246aafdc3c3222789e728e37"
NODE_TYPES_SHA256 = "e696c1156c9916d1d26f2e4643b6d32794dd079b0c8640aa1dabf2f33a3f5cdf"


def _load() -> LanguageGrammar:
    resource = files(__package__).joinpath("node-types.json")
    # Text mode normalizes CRLF/CR to LF before hashing. Git may materialize
    # text files with platform-native line endings, but the grammar identity is
    # defined by canonical UTF-8 JSON content rather than checkout policy.
    text = resource.read_text(encoding="utf-8")
    payload = text.encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != NODE_TYPES_SHA256:
        raise RuntimeError(
            "packaged CMake grammar schema checksum mismatch: "
            f"{digest} != {NODE_TYPES_SHA256}"
        )

    decoded: Any = json.loads(text)
    if not isinstance(decoded, list) or not all(
        isinstance(item, dict) for item in decoded
    ):
        raise RuntimeError("packaged CMake node-types schema has an invalid root")

    return LanguageGrammar.from_node_types(
        language="cmake",
        version=GRAMMAR_VERSION,
        source_revision=GRAMMAR_REVISION,
        source_sha256=NODE_TYPES_SHA256,
        data=decoded,
    )


CMAKE_GRAMMAR = _load()


__all__ = [
    "CMAKE_GRAMMAR",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
    "NODE_TYPES_SHA256",
]
