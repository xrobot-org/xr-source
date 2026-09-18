# xr-source

xr-source is a lossless structured-source library for XRobot tooling.

The core model is language-neutral: immutable syntax nodes, tokens and trivia,
source spans, visitors/rewriters and a document-layout IR. C++ is the first
frontend. CMake already reuses the same core through the optional `cmake`
extra rather than inventing another text manipulation layer.

Primary invariant:

    tree = CppParser().parse(source)
    assert tree.render_bytes() == source

Parsing does not perform C++ name lookup, overload resolution, template
instantiation, type inference or constant evaluation. Semantic providers can be
layered above the syntax model when a consumer needs those services.

C++ support is installed by default. CMake support is optional:

    pip install 'xr-source[cmake]'

## C++

```python
from xr_source.cpp import CppDocument, CppFactory, CppFileBuilder

source = b'''#include "device.hpp"\n\nvoid app_main() {\n  Device device;\n}\n'''
document = CppDocument.parse(source)
assert document.render_bytes() == source

app_main = document.function_views("app_main")[0]
includes = [(item.header, item.system) for item in document.include_views()]
locals_ = document.variable_views(global_scope=False)

factory = CppFactory()
changed = document.insert_after(
    document.includes()[0],
    factory.include("extra.hpp"),
)

builder = CppFileBuilder(header=True)
builder.include("thread.hpp")
entry = builder.function("void", "XRobotMain", prefix=["[[noreturn]]"])
entry.body.call("Run", ["device"])
generated = builder.build()
```

The generic syntax tree still exposes every parser kind and token/trivia byte;
`function_views`, `include_views`, `variable_views`, builders and regions are
convenience layers over that complete representation. The packaged grammar
schema is queryable as data as well:

```python
from xr_source.cpp import CPP_GRAMMAR

binary = CPP_GRAMMAR.require_node("binary_expression", named=True)
assert binary.field_names == ("left", "operator", "right")
assert CPP_GRAMMAR.is_subtype("lambda_expression", "expression")
```

## CMake

```python
from xr_source.cmake import CMakeDocument, CMakeFileBuilder

cmake = CMakeDocument.parse("project(Demo)\nadd_library(foo STATIC foo.cpp)\n")
assert cmake.command_views("add_library")[0].arguments[0].text == "foo"

builder = CMakeFileBuilder()
builder.command("project", ["Demo", "LANGUAGES", "CXX"])
builder.command("add_library", ["foo", "STATIC", "foo.cpp"])
```

See docs/ARCHITECTURE.md and docs/ROADMAP.md.
