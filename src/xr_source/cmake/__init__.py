"""CMake frontend built on the same syntax core and edit model as C++."""

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
