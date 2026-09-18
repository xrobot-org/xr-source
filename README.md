# xr-source

`xr-source` provides lossless, structured source editing for XRobot tooling.

It can read an existing C++/header or CMake file into a queryable syntax tree,
modify selected structure without losing unrelated source text, and generate new
source through the same model.

The main guarantee is source fidelity:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Parser diagnostics do not disable round-trip preservation. Syntax structure and
compiler semantics are deliberately separate: `xr-source` does not perform C++
name lookup, overload resolution, template instantiation, type inference, or
constant evaluation.

## Installation

C++ support is included by default:

```sh
pip install xr-source
```

Install the optional CMake frontend when needed:

```sh
pip install "xr-source[cmake]"
```

Python 3.10 or newer is required.

## What this package is for

The package is intended to replace ad-hoc source manipulation such as:

- string concatenation for generated `.cpp/.hpp` files;
- regular expressions for locating user code regions;
- custom token scanners for common C++ constructs;
- one-off CMake text patching;
- duplicated formatting decisions inside application logic.

It is not a compiler frontend replacement. Compiler-only questions should stay in
the compiler or in an optional semantic provider.

## Files and responsibilities

| Package | Responsibility |
| --- | --- |
| `xr_source.core` | Immutable syntax tree, source spans, rewrites, grammar metadata |
| `xr_source.parser` | Parser backend adapters; Tree-sitter stays behind this boundary |
| `xr_source.format` | Width-aware layout IR used by generated source |
| `xr_source.cpp` | C++ parser, queries, typed views, regions, factories, builders |
| `xr_source.cmake` | CMake parser, command views, factories, builders |
| `docs/REVIEW_GUIDE.md` | Short architecture review path |
| `docs/ARCHITECTURE.md` | Detailed design and invariants |
| `docs/VALIDATION.md` | Corpus, compatibility, packaging and version evidence |

## Read existing C++

```python
from xr_source.cpp import CppDocument

document = CppDocument.parse(
    b"""
#include "device.hpp"

static Device device;

void app_main() {
  XR_REGISTER(device, Base);
}
""".lstrip()
)

assert document.render_bytes().startswith(b'#include "device.hpp"')

include = document.include_views()[0]
assert include.header == "device.hpp"
assert not include.system

function = document.function_views("app_main")[0]
registration = document.call_views("XR_REGISTER")[0]

print(function.name)
print([argument.text for argument in registration.arguments])
```

Common source-level queries include:

```python
document.includes()
document.include_views()
document.functions("app_main")
document.function_views("app_main")
document.classes("Device")
document.class_views("Device")
document.calls("XR_REGISTER")
document.call_views("XR_REGISTER")
document.variable_views()
document.variable_views(global_scope=True)
document.variable_views(global_scope=False)
```

These are convenience views over the complete syntax tree. They do not replace
the underlying grammar representation.

## Edit existing C++

Documents are immutable snapshots. An edit returns a new document.

```python
from xr_source.cpp import CppDocument, CppFactory

document = CppDocument.parse(
    '#include "a.hpp"\n'
    'void app_main() {}\n'
)

factory = CppFactory()

changed = document.insert_after(
    document.includes()[0],
    factory.include("b.hpp"),
    separator="",
)

assert document.render() == '#include "a.hpp"\nvoid app_main() {}\n'
assert changed.render() == (
    '#include "a.hpp"\n'
    '#include "b.hpp"\n'
    'void app_main() {}\n'
)
```

High-level document edits reparse the changed source before returning. This keeps
parser-owned field labels, diagnostics, and error-recovery structure synchronized
with the edited text.

## User code and protected regions

STM32-style user regions are structured instead of copied with regular expressions:

```cpp
/* User Code Begin 3 */
custom_code();
/* User Code End 3 */
```

```python
region = document.user_regions()[0]
print(region.name)
print(region.body_text)

changed = document.replace_region_body(
    region,
    "\ncustom_code();\nother_code();\n",
)
```

The C++ frontend also recognizes:

- `// clang-format off` / `// clang-format on`;
- `// NOLINTBEGIN` / `// NOLINTEND`.

Builders can create the same protected regions when generating new source.

## Generate C++

The builder API produces the same parser-backed syntax model used for parsed
source. There is no separate generated-code AST.

```python
from xr_source.cpp import CppFileBuilder

source = CppFileBuilder(header=True)
source.include("thread.hpp")
source.include("gpio.hpp")

entry = source.function(
    "void",
    "XRobotMain",
    prefix=["[[noreturn]]"],
)
entry.parameter("LibXR::GPIO&", "led")
entry.body.variable(
    "BlinkLED",
    "blink",
    initializer="BlinkLED(led, 250)",
    storage=["static"],
)
entry.body.call("Run", ["blink"])

document = source.build()
print(document.render())
```

For lower-level fragment creation use `CppFactory`:

```python
from xr_source.cpp import CppFactory

factory = CppFactory()

include = factory.include("libxr.hpp")
expression = factory.expression("a + b * c")
statement = factory.call_statement("XR_REGISTER", ["led", "LibXR::GPIO"])
declaration = factory.variable(
    "STM32GPIO",
    "led",
    initializer="GPIOB",
    storage=["static"],
)
```

## C++ grammar access

The complete structural grammar is packaged as versioned data rather than as a
large handwritten Python class hierarchy.

```python
from xr_source.cpp import CPP_GRAMMAR

binary = CPP_GRAMMAR.require_node(
    "binary_expression",
    named=True,
)

assert binary.field_names == ("left", "operator", "right")
assert CPP_GRAMMAR.is_subtype("lambda_expression", "expression")
assert CPP_GRAMMAR.is_subtype("requires_expression", "expression")
```

This grammar layer describes syntax only. It does not answer semantic questions
such as which declaration an identifier refers to.

## CMake

CMake uses the same immutable syntax, rewrite, grammar, and layout infrastructure.

```python
from xr_source.cmake import CMakeDocument

document = CMakeDocument.parse(
    "project(Demo)\n"
    "add_library(foo STATIC foo.cpp)\n"
)

library = document.command_views("add_library")[0]

assert library.name == "add_library"
assert [argument.text for argument in library.arguments] == [
    "foo",
    "STATIC",
    "foo.cpp",
]
```

Generate a new CMake file:

```python
from xr_source.cmake import CMakeFileBuilder

cmake = CMakeFileBuilder()
cmake.command("cmake_minimum_required", ["VERSION", "3.20"])
cmake.command("project", ["Demo", "LANGUAGES", "CXX"])
cmake.command("add_library", ["foo", "STATIC", "foo.cpp"])

document = cmake.build()
print(document.render())
```

## Formatting

Rendering and formatting are separate operations.

- `render()` preserves represented source;
- the layout layer decides how newly generated source wraps and indents.

The layout IR provides small primitives such as:

```text
Text
Concat
Group
Indent
Line
SoftLine
HardLine
IfBreak
```

Language-specific factories use these primitives instead of embedding line-length
logic inside XRobot or LibXR business code.

## Design boundaries

`xr-source` is responsible for source structure:

- source byte preservation;
- syntax nodes, tokens, trivia and spans;
- grammar field/child/subtype contracts;
- immutable structural edits;
- common source-level C++ and CMake views;
- deterministic generated-source layout.

It is intentionally not responsible for:

- C++ name lookup;
- overload resolution;
- template instantiation;
- type inference;
- constant evaluation;
- XRobot constructor/view compatibility;
- hardware registration semantics.

Those belong to the compiler or to the consuming application.

## Parser versions

The validated default C++ backend is currently pinned to:

```text
tree-sitter 0.25.2
tree-sitter-cpp 0.23.4
```

The packaged C++ grammar contract corresponds to upstream revision
`f41e1a044c8a84ea9fa8577fdd2eab92ec96de02`.

CMake uses `tree-sitter-language-pack 1.20.0`, whose pinned CMake grammar is
upstream revision `ca627bb5828616b6246aafdc3c3222789e728e37`.

The exact compatibility reasoning and newer C++ grammar candidate are documented
in `docs/ARCHITECTURE.md` and `docs/VALIDATION.md`.

## Validation

The current review branch is tested on Python 3.10, 3.12, and 3.14.

Validation includes:

- unit and API tests;
- public API documentation coverage;
- ruff;
- mypy strict;
- sdist/wheel build;
- twine metadata validation;
- isolated wheel installation;
- C++/header ecosystem round-trip;
- CMake ecosystem round-trip;
- XRobot Module constructor-interface parity.

See `docs/VALIDATION.md` for the measured corpus and exact results.

## Development

Install all development and CMake dependencies:

```sh
pip install -e ".[dev,cmake]"
```

Run the normal checks:

```sh
python -m pytest
ruff check src tests tools
mypy src
python -m build
twine check dist/*
```

## Review

If you are reviewing the implementation rather than using the package, start with:

```text
docs/REVIEW_GUIDE.md
```

It reduces the runtime design to eight files and explains which generated grammar,
test, and packaging files can be skipped on the first pass.
