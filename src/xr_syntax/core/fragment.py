"""定义带语言归属的可插入语法片段。
Language-tagged syntax fragments used by public edit APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .green import GreenElement
from .text import encode_source


@dataclass(frozen=True)
class SyntaxFragment:
    """保存可插入 green 元素及其语言归属。
    Carry one insertable green element together with explicit language provenance.
    """

    language: str
    green: GreenElement
    opaque: bool = False

    def __post_init__(self) -> None:
        """拒绝空语言标识。
        Reject fragments without an explicit language identifier.
        """
        if not self.language:
            raise ValueError("syntax fragment language must not be empty")

    def render(self) -> str:
        """渲染片段源码文本。
        Render the source text represented by this fragment.
        """
        return self.green.render()

    def render_bytes(self) -> bytes:
        """渲染片段源码字节。
        Render the source bytes represented by this fragment.
        """
        return encode_source(self.render())

    def green_for(self, language: str) -> GreenElement:
        """返回指定语言可用的 green 元素，语言不匹配时拒绝。
        Return the green element for the requested language or reject a mismatch.
        """
        if self.language != language:
            raise ValueError(
                f"fragment language {self.language!r} does not match tree language {language!r}"
            )
        return self.green
