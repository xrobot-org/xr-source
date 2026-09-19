"""可选 parser backend 的命名空间。

基础 C++ frontend 不从这里加载任何第三方 parser。需要 CMake 支持时，
CMake frontend 会显式导入自己的 optional Tree-sitter adapter。

Namespace for optional parser backends. The base C++ frontend does not load a
third-party parser from here.
"""

__all__: list[str] = []
