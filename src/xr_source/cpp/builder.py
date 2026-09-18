"""Structured C++ file, function, and block builders layered on CppFactory."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from xr_source.core import GreenElement
from xr_source.format import Group, Indent, concat, hardline, join, render, softline, verbatim

from .document import CppDocument
from .factory import CppFactory


@dataclass(slots=True)
class CppBlockBuilder:
    """Mutable convenience accumulator for constructing one C++ compound body.

    The builder is only an ergonomic front-end; build products are immutable parser-
    backed GreenElements.
    """
    factory: CppFactory
    items: list[GreenElement] = field(default_factory=list)

    def add(self, element: GreenElement) -> GreenElement:
        """Append the element to this builder and return it."""
        self.items.append(element)
        return element

    def statement(self, source: str) -> GreenElement:
        """Create and append one statement."""
        return self.add(self.factory.statement(source))

    def call(self, callee: str, arguments: Iterable[str] = ()) -> GreenElement:
        """Create and append one call statement."""
        return self.add(self.factory.call_statement(callee, arguments))

    def variable(
        self,
        cpp_type: str,
        name: str,
        *,
        initializer: str | None = None,
        storage: Iterable[str] = (),
    ) -> GreenElement:
        """Create and append one variable declaration."""
        return self.add(
            self.factory.variable(
                cpp_type,
                name,
                initializer=initializer,
                storage=storage,
            )
        )

    def user_region(
        self,
        name: str,
        body: Iterable[GreenElement] = (),
    ) -> GreenElement:
        """Create or append a paired User Code region."""
        return self.add(self.factory.user_region(name, body))

    def format_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """Create or append a clang-format disabled region."""
        return self.add(self.factory.format_region(body))

    def lint_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """Create or append a NOLINT disabled region."""
        return self.add(self.factory.lint_region(body))

    def raw(self, source: str) -> GreenElement:
        """Append or create opaque source text without interpreting its internal structure."""
        return self.add(self.factory.raw(source))


@dataclass(slots=True)
class CppFunctionBuilder:
    """Collect a function signature/body before producing parser-backed syntax."""
    factory: CppFactory
    return_type: str
    name: str
    parameters: list[tuple[str, str]] = field(default_factory=list)
    prefix: list[str] = field(default_factory=list)
    body: CppBlockBuilder = field(init=False)

    def __post_init__(self) -> None:
        self.body = CppBlockBuilder(self.factory)

    def parameter(self, cpp_type: str, name: str) -> CppFunctionBuilder:
        """Append one source-level function parameter."""
        self.parameters.append((cpp_type, name))
        return self

    def build(self) -> GreenElement:
        """Render the signature/body through the layout IR and parse the result as C++ syntax."""
        params = [
            concat(cpp_type, " ", name)
            for cpp_type, name in self.parameters
        ]
        signature = concat(
            " ".join((*self.prefix, self.return_type)).strip(),
            " ",
            self.name,
            Group(
                concat(
                    "(",
                    Indent(concat(softline, join(concat(",", hardline), params))),
                    softline,
                    ")",
                )
            ),
        )
        body = join(hardline, (verbatim(item.render()) for item in self.body.items))
        if self.body.items:
            document = concat(
                signature,
                " {",
                Indent(concat(hardline, body)),
                hardline,
                "}",
            )
        else:
            document = concat(signature, " {}")
        source = render(document, width=self.factory.width)
        return self.factory.declaration(source)


@dataclass(slots=True)
class CppFileBuilder:
    """Top-level C++ source/header builder using CppFactory fragments."""
    factory: CppFactory = field(default_factory=CppFactory)
    header: bool = False
    items: list[GreenElement | CppFunctionBuilder] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.header:
            self.items.append(self.factory.directive("#pragma once"))

    def add(self, element: GreenElement) -> GreenElement:
        """Append the element to this builder and return it."""
        self.items.append(element)
        return element

    def include(self, header: str, *, system: bool = False) -> GreenElement:
        """Create or append one include directive."""
        return self.add(self.factory.include(header, system=system))

    def comment(self, text: str, *, block: bool = False) -> GreenElement:
        """Append or create a source comment."""
        return self.add(self.factory.comment(text, block=block))

    def raw(self, source: str) -> GreenElement:
        """Append or create opaque source text without interpreting its internal structure."""
        return self.add(self.factory.raw(source))

    def format_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """Create or append a clang-format disabled region."""
        return self.add(self.factory.format_region(body))

    def lint_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """Create or append a NOLINT disabled region."""
        return self.add(self.factory.lint_region(body))

    def declaration(self, source: str) -> GreenElement:
        """Create or append one declaration."""
        return self.add(self.factory.declaration(source))

    def variable(
        self,
        cpp_type: str,
        name: str,
        *,
        initializer: str | None = None,
        storage: Iterable[str] = (),
    ) -> GreenElement:
        """Create and append one variable declaration."""
        return self.add(
            self.factory.variable(
                cpp_type,
                name,
                initializer=initializer,
                storage=storage,
            )
        )

    def function(
        self,
        return_type: str,
        name: str,
        *,
        parameters: Iterable[tuple[str, str]] = (),
        prefix: Iterable[str] = (),
    ) -> CppFunctionBuilder:
        """Create a function builder in source order."""
        function = CppFunctionBuilder(
            self.factory,
            return_type,
            name,
            list(parameters),
            list(prefix),
        )
        self.items.append(function)
        return function

    def user_region(
        self,
        name: str,
        body: Iterable[GreenElement] = (),
    ) -> GreenElement:
        """Create or append a paired User Code region."""
        return self.add(self.factory.user_region(name, body))

    def build(self) -> CppDocument:
        """Render accumulated fragments, parse the complete file and return a CppDocument."""
        rendered: list[str] = []
        for item in self.items:
            element = item.build() if isinstance(item, CppFunctionBuilder) else item
            rendered.append(element.render().rstrip("\r\n"))
        source = "\n".join(rendered)
        if source and not source.endswith("\n"):
            source += "\n"
        return CppDocument.parse(source, parser=self.factory.parser)
