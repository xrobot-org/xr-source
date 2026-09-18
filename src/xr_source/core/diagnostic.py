from __future__ import annotations

from dataclasses import dataclass

from .span import SourcePoint, SourceSpan


@dataclass(frozen=True, slots=True)
class Diagnostic:
    message: str
    span: SourceSpan
    start_point: SourcePoint | None = None
    end_point: SourcePoint | None = None
    severity: str = "error"
