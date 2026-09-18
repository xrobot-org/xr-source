from xr_source.cpp import CppDocument, CppFactory


def test_immutable_replace_reuses_unchanged_tree() -> None:
    document = CppDocument.parse("int a = 1;\nint b = 2;\n")
    declarations = document.nodes("declaration")
    replacement = CppFactory().declaration("int a = 42")
    changed = document.tree.replace(declarations[0], replacement)

    assert document.render() == "int a = 1;\nint b = 2;\n"
    assert changed.render() == "int a = 42;\nint b = 2;\n"
    assert changed.green_root.children[-1] is document.tree.green_root.children[-1]
