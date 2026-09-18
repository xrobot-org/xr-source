"""定义 CMake 前端公共接口；它与 C++ 前端共享同一套不可变语法树、重写和布局基础设施。"""

from .builder import CMakeFileBuilder
from .document import CMakeDocument
from .factory import CMakeFactory
from .grammar import CMAKE_GRAMMAR, GRAMMAR_REVISION, GRAMMAR_VERSION
from .parser import CMakeParser
from .view import CMakeArgumentView, CMakeCommandView

__all__ = [
    "CMAKE_GRAMMAR",
    "CMakeArgumentView",
    "CMakeCommandView",
    "CMakeDocument",
    "CMakeFactory",
    "CMakeFileBuilder",
    "CMakeParser",
    "GRAMMAR_REVISION",
    "GRAMMAR_VERSION",
]
