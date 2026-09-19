# 验证状态 / Validation Status

[中文](#中文) | [English](#english)

## 中文

日期：2026-09-18。

本文记录 native C++ parser 迁移后的验证证据。这里严格区分三件事：

1. **源码保真**：parse/render 是否逐字节一致；
2. **结构分类**：parser 是否把目标源码识别成需要的结构；
3. **编译器语义正确性**：代码在某个 toolchain/宏配置下的真实语义。

`xr-source` 的核心承诺是前两项中的源码级能力，不冒充编译器语义分析。

### 正式 CI

当前分支在以下矩阵上运行：

- Ubuntu：Python 3.10 / 3.12 / 3.14；
- Windows：Python 3.10 / 3.12 / 3.14；
- `quality`；
- `package`。

当前 native parser 回归测试：

- pytest：38/38；
- Ruff：通过；
- `mypy --strict`：通过；
- sdist：构建成功；
- pure-Python wheel：构建成功；
- `twine check`：通过；
- 基础 wheel 独立安装：C++ parse smoke test 通过。

### C++ 依赖隔离

基础包：

```toml
dependencies = []
```

C++ 路径明确保证：

- 没有 `tree-sitter-cpp` dependency；
- 没有 `tree-sitter` dependency；
- 没有 C++ Tree-sitter grammar JSON；
- 没有 C++ Tree-sitter license payload；
- C++ import/parse 不经过 `xr_source.parser.tree_sitter`。

Package CI 会：

1. 构建 wheel；
2. 在没有安装 CMake extra 的环境安装基础 wheel；
3. 解析 C++；
4. 检查 package metadata 中没有 `tree-sitter-cpp`；
5. 检查 `sys.modules` 中没有加载 `tree_sitter` / `tree_sitter_cpp`。

CMake 是独立 optional frontend，`xr-source[cmake]` 可以安装 `tree-sitter-language-pack`。

### 无损 round-trip 不变量

每次 native C++ parse 都会直接检查：

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

单测覆盖：

- CRLF；
- 普通注释；
- preprocessor；
- raw string；
- UTF-8 BOM；
- 空 translation unit；
- 不完整/错误源码；
- 非 UTF-8 字节；
- expression replacement 边缘 trivia。

### 公开真实 corpus

在 commit：

```text
0098d1ac34dc400050dd7ccafd27a9cce852031c
```

使用基础包（没有 CMake extra）clone 并解析以下公开仓库：

- `xrobot-org/XRobot`；
- `xrobot-org/libxr`；
- `xrobot-org/BlinkLED`；
- `xrobot-org/DurationStatistics`。

结果：

- 文件数：**1,850**；
- 总字节：**16,624,085 bytes**；
- round-trip failure：**0**；
- 有 parser diagnostics 的文件：4；
- diagnostics 总数：7；
- GitHub Actions Ubuntu runner 用时：73.908 s。

#### Corpus 实际抓到的问题

第一版 native parser 在同一 corpus 上出现过：

```text
123 round-trip failures
```

典型变化：

```text
#endif
      ;
```

错误地变成：

```text
#endif;
```

以及：

```text
Options_ }
```

附近空白被吞掉。

进一步诊断确认 lexer 本身仍然逐字节一致，问题出在 expression parser：

- `_parse_expression()` 会 trim 两端 trivia；
- 部分调用方却用未 trim 的原区间做 replacement；
- replacement 因而把 expression 节点没有表示的空白一起覆盖掉。

修复后统一通过 `_expression_replacement()` 生成 span，使 replacement 区间与 expression 实际表示的 trimmed 区间严格一致。同一 1,850 文件 corpus 随后降到 **0 failure**。

这个案例也是 corpus 验证保留在流程里的原因：单元测试很难覆盖所有“预处理 + 表达式 + trivia”组合。

### 历史大 corpus

在 native parser 迁移前，Tree-sitter-backed prototype 曾跑过更大的本地 corpus：

- 4,420 文件；
- 153,971,079 bytes；
- 0 round-trip failure。

这份结果只作为**历史基线和 corpus 定义**保留，不能冒充 native parser 的验证结果。

后续如果需要宣称 native parser 达到同等级完整本地覆盖，应重新对这 4,420 文件跑一次当前 backend。

### 结构兼容性

当前测试覆盖的 XRobot 相关源码结构包括：

- include；
- class / struct 与 access section；
- function / constructor；
- complex parameter declarator；
- template parameter；
- deleted/defaulted special member；
- 文件作用域和 block 作用域变量；
- call expression 与 arguments；
- lambda / requires / fold / co_await 等现代 C++ 结构分类；
- immutable edit + reparse；
- User Code / format / lint 区域。

遇到没有语义信息就无法可靠细分的结构时，native parser 使用 generic lossless node 保留源码，而不是猜测编译器语义。

### XRobot interface parity 的历史证据

早期 source-model prototype 曾对 66 个 primary Module header 与旧 XRobot parser 做比较：

- 旧 parser 接受 64 个：64/64 constructor name/type/default shape 一致；
- 旧 parser 自己拒绝 2 个；
- 对旧 parser 已接受的接口没有回归。

由于 C++ backend 已经从 Tree-sitter 换成 native parser，这一组属于历史 baseline。正式宣布 consumer migration 完成前，应对当前 native backend 重新跑 parity。

### CMake

CMake 仍使用 optional `tree-sitter-language-pack`：

- grammar metadata 固定版本；
- JSON checksum 在规范化换行后计算，避免 Windows checkout 的 CRLF 改写导致假失败；
- 使用与 C++ 相同的 immutable syntax / rewrite core。

CMake 的测试结果不能被拿来证明 C++ 的 parser independence；二者依赖边界是独立验证的。

### 本地历史 evidence

早期验证文件保存在：

```text
D:/XRobotWork/ecosystem-20260915/evidence/xr-source-20260918/
```

主要文件：

- `cpp-roundtrip-final.json`；
- `cpp-only-roundtrip.json`；
- `cmake-roundtrip.json`；
- `xrobot-interface-compare.json`。

这些是验证产物，不参与 runtime。

## English

Date: 2026-09-18.

This document records evidence for the native C++ parser transition. Source
fidelity, structural classification and compiler semantic validity are separate
properties.

### Current native-parser checks

The native C++ frontend is exercised by the package test suite on Linux and
Windows across Python 3.10, 3.12 and 3.14.

The current native-parser validation reports:

- pytest: 38/38 passed;
- Ruff: all checks passed;
- mypy strict: no issues in 38 source files;
- sdist and pure-Python wheel: build successfully;
- package metadata: sdist and wheel pass `twine check`;
- isolated base-wheel smoke test: C++ parses without installing Tree-sitter.

The normal CI workflow remains the authoritative final matrix check.

### Dependency isolation

The base package declares no runtime dependencies.

C++ specifically has:

- no `tree-sitter-cpp` dependency;
- no `tree-sitter` dependency;
- no packaged C++ Tree-sitter grammar JSON or Tree-sitter C++ license payload;
- no C++ import path through `xr_source.parser.tree_sitter`.

The package CI installs the built wheel into an environment that has only the
build/check tooling, then parses C++ and checks that no Tree-sitter module was
loaded. It also checks wheel metadata for any accidental
`tree-sitter-cpp` requirement.

CMake is intentionally separate: `xr-source[cmake]` may install
`tree-sitter-language-pack` and its Tree-sitter runtime.

### Lossless round-trip contract

The native parser asserts byte fidelity on every parse:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Unit coverage includes CRLF, comments, preprocessor directives, raw strings,
UTF-8 BOM, empty files and malformed/incomplete source.

A native public-corpus run at commit
`0098d1ac34dc400050dd7ccafd27a9cce852031c` cloned the current public
`xrobot-org/XRobot`, `xrobot-org/libxr`, `xrobot-org/BlinkLED` and
`xrobot-org/DurationStatistics` repositories and parsed their C/C++ source
set with the base package only:

- 1,850 files;
- 16,624,085 bytes;
- 0 round-trip failures;
- 4 files with parser diagnostics;
- 7 diagnostics total;
- 73.908 s elapsed on the GitHub Actions Ubuntu runner.

The corpus exposed an expression-replacement span bug in the first native
implementation: 123 files initially lost trivia immediately before delimiters.
The lexer itself remained byte-identical. The parser was changed so every
expression replacement uses the same trimmed span represented by the expression
node, after which the same 1,850-file corpus completed with zero failures.

Before the native parser transition, the Tree-sitter-backed prototype was also
stress-tested on a larger 4,420-file / 153,971,079-byte local ecosystem corpus
with zero round-trip failures. That older run remains the larger historical
baseline, but it is **not** relabeled as native-parser evidence. The larger local
corpus can still be rerun later if an equivalent full-local-corpus native claim
is needed.

### Structural compatibility

The current tests cover the source-level interfaces required by XRobot tooling,
including:

- includes;
- classes and access sections;
- function and constructor views;
- complex parameter declarators;
- template parameters;
- deleted/defaulted special members;
- file- and block-scope variables;
- call expressions and arguments;
- modern C++ syntax categories such as lambda, requires, fold and co_await;
- immutable edits and reparsing;
- protected user/format/lint regions.

The native parser intentionally falls back to generic lossless source nodes
where classification would require semantic knowledge.

### CMake validation

CMake continues to use the optional `tree-sitter-language-pack` backend.
Its grammar metadata remains versioned under
`src/xr_source/cmake/grammar/`. CMake is tested through the same immutable
syntax/rewrite core but is not evidence for the independence of the C++
frontend.

### Historical XRobot compatibility evidence

The earlier source-model prototype compared typed constructor views with the
then-current XRobot Module parser across 66 primary Module headers:

- 64 headers accepted by the XRobot parser: 64/64 constructor
  name/type/default shapes matched;
- 2 headers were already rejected by the XRobot parser;
- 0 regressions among interfaces accepted by that baseline.

Because the C++ backend has now changed, this is historical baseline evidence.
A new native-parser parity run should replace it before declaring corpus-level
migration complete.

### Local evidence directory

Earlier corpus/parity evidence is stored under:

`D:/XRobotWork/ecosystem-20260915/evidence/xr-source-20260918/`

Important historical outputs include:

- `cpp-roundtrip-final.json`;
- `cpp-only-roundtrip.json`;
- `cmake-roundtrip.json`;
- `xrobot-interface-compare.json`.

These files are validation artifacts and are not runtime dependencies.
