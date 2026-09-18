"""提供 C++ 文件、函数和代码块的结构化构建器，生成结果与解析结果使用同一语法模型。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from xr_source.core import GreenElement
from xr_source.format import Group, Indent, concat, hardline, join, render, softline, verbatim

from .document import CppDocument
from .factory import CppFactory

# ---------------------------------------------------------------------------
# 结构化源码生成辅助层
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CppBlockBuilder:
    """用于按顺序累积一个 C++ 复合语句体中各片段的便捷构建器。"""
    factory: CppFactory
    items: list[GreenElement] = field(default_factory=list)

    def add(self, element: GreenElement) -> GreenElement:
        """把一个 green 元素追加到当前代码块构建器，并返回该元素。"""
        self.items.append(element)
        return element

    def statement(self, source: str) -> GreenElement:
        """创建并追加一条 C++ 语句。"""
        return self.add(self.factory.statement(source))

    def call(self, callee: str, arguments: Iterable[str] = ()) -> GreenElement:
        """创建并追加一条函数调用语句。"""
        return self.add(self.factory.call_statement(callee, arguments))

    def variable(
        self,
        cpp_type: str,
        name: str,
        *,
        initializer: str | None = None,
        storage: Iterable[str] = (),
    ) -> GreenElement:
        """创建并追加一条变量声明。"""
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
        """创建并追加一组 User Code 保护区标记及其 body。"""
        return self.add(self.factory.user_region(name, body))

    def format_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建并追加 clang-format off/on 保护区域。"""
        return self.add(self.factory.format_region(body))

    def lint_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建并追加 NOLINTBEGIN/NOLINTEND 保护区域。"""
        return self.add(self.factory.lint_region(body))

    def raw(self, source: str) -> GreenElement:
        """追加一段不解释内部结构的原始 C++ 源码。"""
        return self.add(self.factory.raw(source))


@dataclass(slots=True)
class CppFunctionBuilder:
    """在生成 parser-backed 语法之前收集函数签名、参数和函数体。"""
    factory: CppFactory
    return_type: str
    name: str
    parameters: list[tuple[str, str]] = field(default_factory=list)
    prefix: list[str] = field(default_factory=list)
    body: CppBlockBuilder = field(init=False)

    def __post_init__(self) -> None:
        """为函数构建器创建独立的 CppBlockBuilder 作为函数体累积器。"""
        self.body = CppBlockBuilder(self.factory)

    def parameter(self, cpp_type: str, name: str) -> CppFunctionBuilder:
        """按源码顺序追加一个由类型和名称组成的函数参数。"""
        self.parameters.append((cpp_type, name))
        return self

    def build(self) -> GreenElement:
        """通过布局 IR 渲染函数签名和 body，再解析成统一 green 语法元素。"""
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


# FileBuilder 只是便于调用的可变累积状态；build() 最终一定返回不可变、
# parser-backed 的 CppDocument，使“生成源码”和“解析已有源码”汇合到同一模型。
@dataclass(slots=True)
class CppFileBuilder:
    """用于构建完整 C++ 源文件或头文件的顶层构建器。"""
    factory: CppFactory = field(default_factory=CppFactory)
    header: bool = False
    items: list[GreenElement | CppFunctionBuilder] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化底层 CppFactory，并在头文件模式下准备 pragma once。"""
        if self.header:
            self.items.append(self.factory.directive("#pragma once"))

    def add(self, element: GreenElement) -> GreenElement:
        """把一个 green 元素追加到文件构建器并原样返回。"""
        self.items.append(element)
        return element

    def include(self, header: str, *, system: bool = False) -> GreenElement:
        """创建并追加一条 include 指令。"""
        return self.add(self.factory.include(header, system=system))

    def comment(self, text: str, *, block: bool = False) -> GreenElement:
        """创建并追加一条源码注释。"""
        return self.add(self.factory.comment(text, block=block))

    def raw(self, source: str) -> GreenElement:
        """追加一段不解释内部结构的原始 C++ 源码。"""
        return self.add(self.factory.raw(source))

    def format_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建并追加 clang-format 禁用区域。"""
        return self.add(self.factory.format_region(body))

    def lint_disabled(self, body: Iterable[GreenElement]) -> GreenElement:
        """创建并追加 NOLINT 禁用区域。"""
        return self.add(self.factory.lint_region(body))

    def declaration(self, source: str) -> GreenElement:
        """创建并追加一条顶层 C++ 声明。"""
        return self.add(self.factory.declaration(source))

    def variable(
        self,
        cpp_type: str,
        name: str,
        *,
        initializer: str | None = None,
        storage: Iterable[str] = (),
    ) -> GreenElement:
        """创建并追加一条顶层变量声明。"""
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
        """创建函数构建器并把它按源码顺序挂到当前文件。"""
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
        """创建并追加一组 User Code 保护区域。"""
        return self.add(self.factory.user_region(name, body))

    def build(self) -> CppDocument:
        """渲染全部片段并重新解析，返回完整 CppDocument。"""
        rendered: list[str] = []
        for item in self.items:
            element = item.build() if isinstance(item, CppFunctionBuilder) else item
            rendered.append(element.render().rstrip("\r\n"))
        source = "\n".join(rendered)
        if source and not source.endswith("\n"):
            source += "\n"
        return CppDocument.parse(source, parser=self.factory.parser)
