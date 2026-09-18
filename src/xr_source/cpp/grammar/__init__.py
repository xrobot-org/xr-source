"""Checksummed C++ grammar metadata pinned to the validated upstream revision."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from typing import Any

from xr_source.core import LanguageGrammar

GRAMMAR_VERSION = "0.23.4"
GRAMMAR_REVISION = "f41e1a044c8a84ea9fa8577fdd2eab92ec96de02"
NODE_TYPES_SHA256 = "fdfd4b1f3dca1516616a1eb615bb6c1ad3082b8937ad21070d0def5dcfe7e535"


def _load() -> LanguageGrammar:
    resource = files(__package__).joinpath("node-types.json")
    payload = resource.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != NODE_TYPES_SHA256:
        raise RuntimeError(
            "packaged C++ grammar schema checksum mismatch: "
            f"{digest} != {NODE_TYPES_SHA256}"
        )

    decoded: Any = json.loads(payload)
    if not isinstance(decoded, list) or not all(
        isinstance(item, dict) for item in decoded
    ):
        raise RuntimeError("packaged C++ node-types schema has an invalid root")

    return LanguageGrammar.from_node_types(
        language="cpp",
        version=GRAMMAR_VERSION,
        source_revision=GRAMMAR_REVISION,
        source_sha256=NODE_TYPES_SHA256,
        data=decoded,
    )


CPP_GRAMMAR = _load()


__all__ = [
    "CPP_GRAMMAR",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
    "NODE_TYPES_SHA256",
]
