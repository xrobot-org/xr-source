"""Runtime node-kind and field identifiers exposed by a concrete parser binary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParserKindInfo:
    """Describe one runtime parser kind id/name/named identity."""
    id: int
    name: str
    named: bool


@dataclass(frozen=True, slots=True)
class ParserSchema:
    """Runtime kind/field identifiers exposed by a concrete parser backend.

    This is intentionally smaller than LanguageGrammar. ParserSchema describes
    what the loaded parser binary calls its node kinds and field ids;
    LanguageGrammar describes structural node contracts from node-types.json.
    """

    language: str
    kinds: tuple[ParserKindInfo, ...]
    fields: tuple[str, ...]

    def kind(self, name: str) -> ParserKindInfo | None:
        """Look up one runtime parser kind by spelling."""
        return next((kind for kind in self.kinds if kind.name == name), None)

    @property
    def kind_names(self) -> frozenset[str]:
        """Return every kind spelling exported by the loaded parser binary."""
        return frozenset(kind.name for kind in self.kinds)
