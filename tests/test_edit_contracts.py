"""验证低层编辑的语言归属、fragment 和 diagnostics 契约。
Test low-level edit contracts for language provenance, fragments, and diagnostics.
"""

from __future__ import annotations

import pytest

from xr_syntax.cmake import CMakeDocument, CMakeFactory
from xr_syntax.core import GreenToken
from xr_syntax.core.rewriter import SyntaxRewriter
from xr_syntax.cpp import CppDocument, CppFactory


def test_same_language_element_from_another_snapshot_is_allowed() -> None:
    """同语言 red 元素可作为跨快照 replacement。
    Allow a red element from another snapshot when both trees use the same language.
    """
    target_document = CppDocument.parse("int a = 1;\n")
    source_document = CppDocument.parse("int b = 2;\n")

    changed = target_document.tree.replace(
        target_document.nodes("declaration")[0],
        source_document.nodes("declaration")[0],
    )

    assert changed.render() == "int b = 2;\n"
    assert changed.diagnostics is None
    assert changed.diagnostic_state == "unknown"


def test_cross_language_red_element_is_rejected() -> None:
    """低层编辑拒绝来自其他语言的 red 元素。
    Reject red elements whose owning tree uses another language.
    """
    cpp = CppDocument.parse("int a = 1;\n")
    cmake = CMakeDocument.parse("project(Demo)\n")

    with pytest.raises(ValueError, match="element language"):
        cpp.tree.replace(
            cpp.nodes("declaration")[0],
            cmake.commands("project")[0],
        )


def test_cross_language_fragment_is_rejected() -> None:
    """低层编辑拒绝带其他语言 provenance 的 fragment。
    Reject fragments carrying provenance for another language.
    """
    cpp = CppDocument.parse("int a = 1;\n")
    fragment = CMakeFactory().command("project", ["Demo"])

    with pytest.raises(ValueError, match="fragment language"):
        cpp.tree.replace(cpp.nodes("declaration")[0], fragment)


def test_bare_green_requires_explicit_fragment_provenance() -> None:
    """公共低层编辑不接受缺少语言归属的裸 green 元素。
    Require explicit language provenance instead of accepting bare green elements.
    """
    cpp = CppDocument.parse("int a = 1;\n")
    fragment = CppFactory().declaration("int b = 2")

    with pytest.raises(TypeError, match="SyntaxFragment"):
        cpp.tree.replace(cpp.nodes("declaration")[0], fragment.green)  # type: ignore[arg-type]


def test_factory_fragments_expose_language_and_opaque_state() -> None:
    """factory 生成的 fragment 明确记录语言，raw fragment 标记为 opaque。
    Factory fragments carry a language tag and mark raw text as opaque.
    """
    factory = CppFactory()
    parsed = factory.declaration("int value = 1")
    raw = factory.raw("/* generated elsewhere */")

    assert parsed.language == "cpp"
    assert not parsed.opaque
    assert raw.language == "cpp"
    assert raw.opaque


def test_high_level_edit_reparses_and_restores_diagnostics() -> None:
    """高层文档编辑重新解析，因此 diagnostics 再次可信。
    High-level document edits reparse so diagnostics become authoritative again.
    """
    document = CppDocument.parse("int a = 1;\n")
    target = document.nodes("declaration")[0]

    low_level = document.tree.replace(target, CppFactory().declaration("int b = 2"))
    assert low_level.diagnostic_state == "unknown"
    assert low_level.diagnostics is None

    high_level = document.replace(target, CppFactory().declaration("int b = 2"))
    assert high_level.tree.diagnostic_state == "clean"
    assert high_level.diagnostics == ()


class _RenameToken(SyntaxRewriter):
    """测试用 rewriter，把指定 token 文本替换为新文本。
    Test rewriter that replaces one token spelling.
    """

    def visit_token(self, token: GreenToken):  # type: ignore[override]
        """替换 a 标识符，其余 token 保持 identity。
        Replace the identifier a while preserving every other token.
        """
        if token.text == "a":
            return GreenToken(token.kind, "renamed", token.named, token.missing, token.error)
        return token


def test_rewriter_keeps_diagnostics_only_when_tree_is_unchanged() -> None:
    """rewriter 修改源码后 diagnostics 变为 unknown；无修改时保留原 tree。
    A changed rewrite invalidates diagnostics while a no-op rewrite returns the original tree.
    """
    document = CppDocument.parse("int a = 1;\n")

    unchanged = SyntaxRewriter().rewrite(document.tree)
    assert unchanged is document.tree
    assert unchanged.diagnostic_state == "clean"

    changed = _RenameToken().rewrite(document.tree)
    assert changed is not document.tree
    assert changed.render() == "int renamed = 1;\n"
    assert changed.diagnostics is None
    assert changed.diagnostic_state == "unknown"


def test_builder_rejects_source_draft_from_another_language() -> None:
    """Builder 不接受其他语言的未解析 SourceDraft。
    Builders reject unparsed source drafts carrying another language tag.
    """
    from xr_syntax.cmake import CMakeFileBuilder
    from xr_syntax.cpp import CppFileBuilder

    cmake = CMakeFileBuilder()
    cmake_draft = cmake.command("project", ["Demo"])
    cpp = CppFileBuilder()

    with pytest.raises(ValueError, match="draft language"):
        cpp.add(cmake_draft)
