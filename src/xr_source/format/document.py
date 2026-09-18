"""Small Prettier-style layout IR for deterministic line breaking and indentation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class Doc:
    """Base type for the language-neutral layout document IR."""
    pass


@dataclass(frozen=True, slots=True)
class Text(Doc):
    """Literal output text that never participates in line breaking."""
    value: str


@dataclass(frozen=True, slots=True)
class Line(Doc):
    """Potential line break. In flat mode it emits flat; in break mode it emits a newline."""
    flat: str = " "
    hard: bool = False


@dataclass(frozen=True, slots=True)
class Concat(Doc):
    """Ordered concatenation of layout documents."""
    parts: tuple[Doc, ...]


@dataclass(frozen=True, slots=True)
class Indent(Doc):
    """Increase indentation for line breaks inside content."""
    content: Doc
    levels: int = 1


@dataclass(frozen=True, slots=True)
class Group(Doc):
    """Prefer a flat rendering when the complete group fits the remaining width."""
    content: Doc


@dataclass(frozen=True, slots=True)
class IfBreak(Doc):
    """Select different layout content depending on whether the enclosing group breaks."""
    broken: Doc
    flat: Doc


class _Mode(Enum):
    FLAT = 1
    BREAK = 2


def text(value: str) -> Doc:
    """Wrap literal text as a layout document."""
    return Text(value)


softline = Line("", False)
line = Line(" ", False)
hardline = Line("", True)


def concat(*parts: Doc | str) -> Doc:
    """Concatenate strings/documents without deciding line breaks."""
    docs = tuple(Text(part) if isinstance(part, str) else part for part in parts)
    if len(docs) == 1:
        return docs[0]
    return Concat(docs)


def verbatim(value: str) -> Doc:
    """Represent existing multi-line text without normalizing its contents."""
    lines = value.splitlines()
    if not lines:
        return Text("")
    parts: list[Doc] = []
    for index, item in enumerate(lines):
        if index:
            parts.append(hardline)
        parts.append(Text(item))
    if value.endswith(("\n", "\r")):
        parts.append(hardline)
    return Concat(tuple(parts))


def join(separator: Doc | str, docs: Iterable[Doc | str]) -> Doc:
    """Join a sequence of documents with one layout separator."""
    sep = Text(separator) if isinstance(separator, str) else separator
    result: list[Doc] = []
    for item in docs:
        if result:
            result.append(sep)
        result.append(Text(item) if isinstance(item, str) else item)
    return Concat(tuple(result))


def render(doc: Doc, *, width: int = 88, indent: str = "  ") -> str:
    """Resolve groups/line breaks into final text for the requested width and indent unit."""
    output: list[str] = []
    column = 0
    stack: list[tuple[int, _Mode, Doc]] = [(0, _Mode.BREAK, doc)]

    while stack:
        level, mode, current = stack.pop()
        if isinstance(current, Text):
            output.append(current.value)
            if "\n" in current.value:
                column = len(current.value.rsplit("\n", 1)[1])
            else:
                column += len(current.value)
        elif isinstance(current, Line):
            if mode is _Mode.FLAT and not current.hard:
                output.append(current.flat)
                column += len(current.flat)
            else:
                padding = indent * level
                output.extend(("\n", padding))
                column = len(padding)
        elif isinstance(current, Concat):
            for part in reversed(current.parts):
                stack.append((level, mode, part))
        elif isinstance(current, Indent):
            stack.append((level + current.levels, mode, current.content))
        elif isinstance(current, IfBreak):
            stack.append(
                (level, mode, current.flat if mode is _Mode.FLAT else current.broken)
            )
        elif isinstance(current, Group):
            # A group is the only place that chooses between flat and broken
            # layout. Nested Line nodes merely obey the selected mode.
            trial = (level, _Mode.FLAT, current.content)
            selected = (
                _Mode.FLAT
                if _fits(width - column, [trial, *stack])
                else _Mode.BREAK
            )
            stack.append((level, selected, current.content))
        else:
            raise TypeError(type(current))
    return "".join(output)


def _fits(remaining: int, stack: list[tuple[int, _Mode, Doc]]) -> bool:
    # Speculatively walk the pending document in flat mode. Encountering a real
    # line break means the current group may stop measuring: later text starts on
    # a fresh line and therefore cannot make this line overflow.
    work = list(stack)
    while remaining >= 0 and work:
        level, mode, current = work.pop(0)
        if isinstance(current, Text):
            if "\n" in current.value:
                return True
            remaining -= len(current.value)
        elif isinstance(current, Line):
            if current.hard or mode is _Mode.BREAK:
                return True
            remaining -= len(current.flat)
        elif isinstance(current, Concat):
            work[0:0] = [(level, mode, part) for part in current.parts]
        elif isinstance(current, Indent):
            work.insert(0, (level + current.levels, mode, current.content))
        elif isinstance(current, IfBreak):
            work.insert(
                0,
                (level, mode, current.flat if mode is _Mode.FLAT else current.broken),
            )
        elif isinstance(current, Group):
            work.insert(0, (level, _Mode.FLAT, current.content))
    return remaining >= 0
