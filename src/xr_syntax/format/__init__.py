"""集中导出语言无关的布局文档 IR 与常用换行原语。
Public layout-document primitives used by language-specific source formatters.
"""

from .document import (
    Concat,
    Doc,
    Group,
    IfBreak,
    Indent,
    Line,
    Text,
    concat,
    hardline,
    join,
    line,
    render,
    softline,
    text,
    verbatim,
)

# ---------------------------------------------------------------------------
# 模块实现：集中导出语言无关的布局文档 IR 与常用换行原语。
# ---------------------------------------------------------------------------

__all__ = [
    "Concat",
    "Doc",
    "Group",
    "IfBreak",
    "Indent",
    "Line",
    "Text",
    "concat",
    "hardline",
    "join",
    "line",
    "render",
    "softline",
    "text",
    "verbatim",
]
