"""Byte-based source locations shared by syntax views and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class SourcePoint:
    """Zero-based row/column location reported by the parser backend."""
    row: int
    column: int


@dataclass(frozen=True, slots=True, order=True)
class SourceSpan:
    """Half-open byte range [start, end) in the original source encoding."""
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid source span [{self.start}, {self.end})")

    @property
    def length(self) -> int:
        """Return the number of bytes covered by this half-open span."""
        return self.end - self.start

    def contains(self, offset: int) -> bool:
        """Return whether a byte offset lies inside this half-open span."""
        return self.start <= offset < self.end
