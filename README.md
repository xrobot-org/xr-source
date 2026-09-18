# xr-source

`xr-source` 是面向 XRobot 工具链的**无损、结构化源码模型与重写基础设施**。

它可以把现有的 C++/头文件或 CMake 文件读成可查询的语法树，在不破坏无关源码的前提下修改指定结构，也可以通过同一套语法模型生成新源码。

最核心的不变量是源码保真：

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Parser 可以产生诊断，但诊断不能成为丢失源码字节的理由。`xr-source` 只处理**源码结构**，不承担 C++ 编译器语义工作，例如名称查找、重载决议、模板实例化、类型推导或常量求值。

## 安装

C++ 前端默认包含，而且**基础安装没有运行时依赖**：

```sh
pip install xr-source
```

需要 CMake 前端时再安装可选依赖：

```sh
pip install "xr-source[cmake]"
```

当前要求 Python 3.10 及以上版本。

## 这个包解决什么问题

目标是替换项目里分散、难维护的源码处理方式，例如：

- 用字符串拼接生成 `.cpp/.hpp`；
- 用正则查找 User Code 区域；
- 为常见 C++ 结构各写一套临时 token scanner；
- 对 CMake 做一次性文本 patch；
- 在 XRobot/LibXR 业务代码里重复实现换行和缩进逻辑。

它**不是**编译器前端的替代品。需要回答“这个名字绑定到哪个声明”“最终选中了哪个重载”“模板实例化后是什么类型”之类的问题时，应交给编译器或独立的可选 semantic provider。

## 目录职责

| 包/文件 | 职责 |
| --- | --- |
| `xr_source.core` | 不可变 green/red 语法树、源码范围、重写、grammar 合同 |
| `xr_source.cpp` | 自有 C++ lexer/parser、查询、类型化视图、区域、factory、builder |
| `xr_source.format` | 新生成源码使用的宽度感知布局 IR |
| `xr_source.parser` | 可选 parser backend 适配层；当前主要服务 CMake |
| `xr_source.cmake` | CMake parser、命令视图、factory、builder |
| `docs/REVIEW_GUIDE.md` | 最短代码审查路径 |
| `docs/ARCHITECTURE.md` | 分层设计与核心不变量 |
| `docs/VALIDATION.md` | 测试、corpus、依赖隔离和打包证据 |
| `docs/ROADMAP.md` | 后续演进计划 |

## 读取现有 C++

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

常用源码级查询包括：

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

这些都是完整语法树之上的便捷视图，不是另一套简化 AST，也不会替代底层 grammar 表示。

## 修改现有 C++

文档对象是不可变快照。任何编辑都会返回新的文档：

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

底层 `SyntaxTree` 编辑会复用没有变化的 green 子树；高层 `CppDocument`/`CMakeDocument` 在编辑后会把结果重新解析一次，从而保证 parser 管理的 field、诊断和错误恢复结构不会过期。

## User Code 与受保护区域

STM32 风格 User Code 区域是正式结构，而不是靠正则复制：

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

C++ 前端还识别：

- `// clang-format off` / `// clang-format on`；
- `// NOLINTBEGIN` / `// NOLINTEND`。

Builder 也可以生成同样的成对区域。

## 生成 C++

Builder 生成的不是另一套“生成 AST”，而是最终仍会进入同一个 parser-backed 语法模型：

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

需要更底层的片段构造时使用 `CppFactory`：

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

## 自有 C++ parser

C++ 前端已经彻底去掉 `tree-sitter-cpp`：

```text
xr-source native C++ source parser
grammar: xr-cpp-0.1
base runtime dependencies: none
tree-sitter-cpp: none
```

当前 C++ 路径由以下层组成：

```text
lossless lexer
    ↓
source-level structural parser
    ↓
GreenNode / GreenToken / GreenTrivia
    ↓
SyntaxTree / CppDocument / typed views
```

Parser 只做源码级结构化，不做编译器语义。对于无法在没有语义信息的情况下安全分类的结构，优先保留成 generic lossless source node，而不是冒险猜错并破坏源码。

## C++ grammar 合同

C++ grammar 合同由 `xr-source` 自己维护，不再从 `tree-sitter-cpp/node-types.json` 读取：

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

这一层描述的是语法结构合同，不回答 identifier 绑定、重载选择等语义问题。

## CMake

CMake 使用与 C++ 相同的不可变语法树、重写和布局核心，但 parser backend 是独立可选依赖：

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

生成新的 CMake 文件：

```python
from xr_source.cmake import CMakeFileBuilder

cmake = CMakeFileBuilder()
cmake.command("cmake_minimum_required", ["VERSION", "3.20"])
cmake.command("project", ["Demo", "LANGUAGES", "CXX"])
cmake.command("add_library", ["foo", "STATIC", "foo.cpp"])

document = cmake.build()
print(document.render())
```

当前 `xr-source[cmake]` 使用 `tree-sitter-language-pack 1.20.0`。这个依赖**不会进入 C++ frontend 的运行路径**。

## 格式化

`render()` 和 format 是两件事：

- `render()`：原样输出当前语法模型代表的源码；
- layout IR：决定**新生成源码**如何换行和缩进。

当前布局 IR 包含：

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

语言层 factory 通过这些 primitive 生成源码，避免把行宽判断和缩进策略散落到 XRobot/LibXR 业务代码里。

## 设计边界

`xr-source` 负责：

- 源码字节保真；
- node/token/trivia/span；
- grammar field/children/subtype 合同；
- 不可变结构编辑；
- C++/CMake 的常用源码级视图；
- 新生成源码的确定性布局。

`xr-source` 不负责：

- C++ 名称查找；
- 重载决议；
- 模板实例化；
- 类型推导；
- 常量求值；
- XRobot 构造函数/view 兼容策略；
- 硬件注册语义。

## 当前验证状态

当前 feature 分支已经验证：

- Python 3.10 / 3.12 / 3.14；
- Linux / Windows；
- `pytest`、Ruff、`mypy --strict`；
- sdist / pure-Python wheel / `twine check`；
- 基础 wheel 独立安装时 C++ 不加载 Tree-sitter；
- 公开真实 C/C++ corpus：1,850 文件、16,624,085 bytes、0 round-trip failure。

详细数据见 `docs/VALIDATION.md`。

## 开发

安装开发依赖和 CMake extra：

```sh
pip install -e ".[dev,cmake]"
```

常规检查：

```sh
python -m pytest
python tools/check_chinese_docs.py
ruff check src tests tools
mypy src
python -m build
twine check dist/*
```

## 代码审查入口

如果目的是审查实现而不是直接使用 API，先看：

```text
docs/REVIEW_GUIDE.md
```

它给出从 immutable syntax core 到 native C++ lexer/parser、typed views、builder 和 optional CMake backend 的最短阅读路径。
