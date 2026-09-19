# XR Syntax

C++ / CMake 源码解析、重写与代码生成工具 / C++ and CMake source parsing, rewriting and code generation toolkit

`xr-syntax` 为 XRobot 和 LibXR 的 Python 工具提供统一的源码表示。它可以读取现有源码、按结构查询和修改，也可以用同一套模型生成新代码。  
`xr-syntax` provides one source model for XRobot and LibXR Python tooling. It reads existing source, supports structured queries and edits, and generates new code through the same model.

## 🌟 功能 / Features

- **无损解析 / Lossless parsing**  
  `parse()` 后再 `render()` 保留原始源码字节，包括空白、换行和注释。  
  Parsing and rendering preserves the original source bytes, including whitespace, line endings, and comments.

- **C++ 与 CMake / C++ and CMake**  
  两种语言都包含在基础安装中，不需要额外 extra。  
  Both frontends are included in the base package; no extra installation is required.

- **结构化查询与修改 / Structured queries and edits**  
  可以按函数、类、调用、变量或 CMake 命令定位结构，并返回新的不可变文档快照。  
  Query functions, classes, calls, variables, and CMake commands, then produce a new immutable document snapshot after edits.

- **生成与解析共用模型 / One model for parsing and generation**  
  Factory 和 builder 生成的源码会回到同一套语法树中。  
  Factory and builder output returns to the same syntax representation used by parsed files.

- **格式化布局 / Formatting layout**  
  新生成代码使用独立的 layout IR 控制换行和缩进，不改动已有源码的 trivia。  
  Generated code uses a separate layout IR for wrapping and indentation without normalizing trivia in existing source.

## 📥 安装 / Installation

Python 3.8 及以上版本。  
Python 3.8 or newer is required.

```bash
pip install xr-syntax
```

从源码安装 / Install from source:

```bash
git clone https://github.com/xrobot-org/xr-source.git
cd xr-source
pip install .
```

## C++ 示例 / C++ Example

```python
from xr_syntax.cpp import CppDocument

source = b'''#include "device.hpp"\n\nvoid app_main() {\n  XR_REGISTER(device, Base);\n}\n'''
document = CppDocument.parse(source)

assert document.render_bytes() == source
print(document.function_views("app_main")[0].name)
print(document.call_views("XR_REGISTER")[0].arguments[0].text)
```

常用查询 / Common queries:

```python
document.include_views()
document.function_views()
document.class_views()
document.call_views()
document.variable_views()
```

## CMake 示例 / CMake Example

```python
from xr_syntax.cmake import CMakeDocument

source = b'''project(Demo)\nadd_library(foo STATIC foo.cpp)\n'''
document = CMakeDocument.parse(source)

assert document.render_bytes() == source
print(document.command_views("add_library")[0].arguments[0].text)
```

CMake parser 由本项目直接实现，与 C++ frontend 一样包含在基础包中。  
The CMake parser is implemented in this project and ships in the base package with the C++ frontend.

## 生成源码 / Generate Source

```python
from xr_syntax.cpp import CppFileBuilder

builder = CppFileBuilder()
builder.include("device.hpp")
builder.raw("\nstatic Device device;\n")
document = builder.build()
print(document.render())
```

```python
from xr_syntax.cmake import CMakeFileBuilder

builder = CMakeFileBuilder()
builder.command("project", ["Demo", "LANGUAGES", "CXX"])
builder.command("add_library", ["foo", "STATIC", "foo.cpp"])
print(builder.build().render())
```

## 目录 / Packages

| 模块 / Module | 内容 / Purpose |
| --- | --- |
| `xr_syntax.core` | 不可变语法树、源码范围和重写 / Immutable syntax trees, spans, and rewrites |
| `xr_syntax.cpp` | C++ parser、查询、view、factory、builder |
| `xr_syntax.cmake` | CMake parser、查询、view、factory、builder |
| `xr_syntax.format` | 生成源码使用的布局 IR / Layout IR for generated source |

需要名称解析、重载决议或类型信息时，可以在 syntax tree 上接编译器或项目自己的 semantic provider。  
Name resolution, overload results, and type information can be supplied by a compiler or project-specific semantic provider above the syntax tree.

## 📖 文档 / Documentation

- [架构 / Architecture](docs/ARCHITECTURE.md)
- [审核顺序 / Review Guide](docs/REVIEW_GUIDE.md)
- [验证 / Validation](docs/VALIDATION.md)
- [路线图 / Roadmap](docs/ROADMAP.md)
