# 代码审查指南 / Review Guide

[中文](#中文) | [English](#english)

## 中文

这个包文件不少，但审查架构时不需要从头到尾把所有文件都看一遍。建议按下面顺序阅读。

### 第一组：语法核心

#### 1. `src/xr_source/core/green.py`

重点看：

- 为什么 green element 不保存 parent/offset；
- node/token/trivia 如何共同覆盖全部源码；
- `replacing_child` / `inserting_child` / `removing_child` 如何保持不可变。

#### 2. `src/xr_source/core/red.py`

重点看：

- red view 如何补 parent/index/field/offset；
- offset 为什么由 child byte width 推导；
- path 为什么只在当前快照内有效。

#### 3. `src/xr_source/core/tree.py`

重点看：

- 低层 replace/remove/insert 如何只重建编辑路径；
- 为什么底层 `SyntaxTree` 不自动重新解析。

#### 4. `src/xr_source/core/document.py`

重点看：

- 高层文档编辑为何在修改后重新解析；
- parser-owned field 和 diagnostics 如何保持新鲜；
- language-neutral API 与具体语言 parser 如何解耦。

#### 5. `src/xr_source/core/grammar.py`

重点看：

- `LanguageGrammar` / `GrammarNodeSpec` / `GrammarSlot`；
- subtype 只表达语法分类，不做类型系统推导；
- C++ native grammar 与 CMake node-types 如何共享同一抽象。

### 第二组：Native C++ frontend

#### 6. `src/xr_source/cpp/lexer.py`

重点看：

- whitespace / newline / comment / literal / punctuation 如何无损切分；
- raw string 和非 UTF-8 round-trip 如何处理；
- 为什么行尾换行单独成 lexeme。

#### 7. `src/xr_source/cpp/parser.py`

这里是 native C++ 结构 parser 的总入口：

- translation unit；
- scope；
- preprocessor；
- template；
- class；
- namespace。

#### 8. 内部解析阶段

```text
src/xr_source/cpp/_ranges.py
src/xr_source/cpp/_declarator.py
src/xr_source/cpp/_declaration.py
src/xr_source/cpp/_expression.py
src/xr_source/cpp/_support.py
```

这些文件把区间扫描、declarator、声明、表达式和严格类型合同拆开，避免把 parser 堆成一个大文件。

其中 `_expression_replacement()` 值得重点看：expression parser 会 trim 两端 trivia，所以 replacement span 必须与实际被 expression 节点表示的 trimmed span 一致，否则会吞掉空白或预处理换行。这个问题曾被真实 corpus 抓到并修复。

#### 9. `src/xr_source/cpp/document.py` 与 `view.py`

看这些便捷 API 有没有越过“源码结构”的边界：

- function/class/call/variable query；
- constructor 识别；
- access section；
- User Code / format / lint region。

它们不应该做重载决议、继承构造推导或类型转换判断。

#### 10. `src/xr_source/cpp/factory.py` 与 `builder.py`

确认“生成源码”和“读取已有源码”是不是最终进入同一语法模型，而不是维护两套 AST。

### 第三组：布局与可选 CMake

#### 11. `src/xr_source/format/document.py`

看：

- `Text / Line / Group / Indent / IfBreak`；
- `_fits()` 如何试算单行是否放得下；
- 为什么这个 formatter 只负责新生成源码，不改 parsed source trivia。

#### 12. CMake

```text
src/xr_source/cmake/
src/xr_source/parser/tree_sitter.py
```

只有在审查 optional CMake frontend 时才需要看 Tree-sitter adapter。C++ 路径不经过这里。

### 第一遍可以跳过的文件

- `src/xr_source/cpp/grammar/__init__.py`：native C++ grammar 合同数据；
- `src/xr_source/cmake/grammar/node-types.json`：CMake grammar 数据；
- grammar LICENSE：第三方 attribution；
- `tests/`：验证证据，不是架构入口；
- `tools/`：corpus/parity/文档审计工具。

### 核心不变量

#### 1. parse/render 必须无损

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

有 diagnostics 也不能破坏这个不变量。

#### 2. Green 不知道绝对位置

GreenNode 可以被其他不可变快照复用；绝对 offset 只属于 red view。

#### 3. C++ parser 属于 xr-source 自己

基础 C++ frontend 是：

```text
native lexer + structural parser + native grammar contract
```

没有 Tree-sitter C++ runtime。

#### 4. Grammar 是结构数据，不是手写巨型 AST 层次

Consumer 依赖统一 grammar 合同和 typed convenience view，不依赖某个第三方 parser 的 Node 对象。

#### 5. Syntax 不等于 semantics

不要在 core 里加入 name lookup、overload resolution、template instantiation、type inference 等编译器职责。

#### 6. Render 与 format 分开

已有源码的 `render()` 应原样还原；只有新生成源码才走 layout IR。

### 建议审查问题

- 任意源码字节是否都能在语法表示里找到？
- 是否有语言特定逻辑泄漏进 `core/`？
- C++ import path 是否偷偷加载第三方 parser？
- 是否引入了第二份重复源码状态？
- convenience view 是否开始冒充不完整的 semantic AST？
- 编辑是否保持不可变和 snapshot-safe？
- format 决策是否泄漏回 XRobot/LibXR 业务逻辑？

## English

The fastest review path is the immutable syntax core followed by the native C++
frontend. CMake is an optional frontend and can be reviewed separately.

### Read these first

1. `src/xr_source/core/green.py`
   - immutable, position-independent syntax storage;
   - every source byte ultimately belongs to a node, token or trivia object.

2. `src/xr_source/core/red.py`
   - parent/field/offset views layered over green storage;
   - positions are derived, not stored in green nodes.

3. `src/xr_source/core/grammar.py`
   - language-neutral structural grammar data model;
   - shared by native C++ and optional CMake.

4. `src/xr_source/cpp/lexer.py`
   - self-contained lossless C++ lexical layer;
   - preserves whitespace, line endings, comments, literals and otherwise
     unclassified source.

5. `src/xr_source/cpp/parser.py`
   - native C++ structural parser and scope/preprocessor orchestration;
   - does not import Tree-sitter or compiler libraries.

6. `src/xr_source/cpp/_declarator.py`,
   `_declaration.py`, `_expression.py`, `_ranges.py`
   - focused internal parsing stages instead of one monolithic parser file.

7. `src/xr_source/cpp/document.py` and `view.py`
   - C++ queries, typed convenience views and protected source regions;
   - deliberately contain no XRobot-specific semantics.

8. `src/xr_source/cpp/builder.py` and `factory.py`
   - structured source generation through the same parseable representation.

Then read `src/xr_source/format/document.py` for generated-code layout and the
`cmake/` plus `parser/tree_sitter.py` paths only if reviewing optional CMake
support.

### Files you can mostly skip on the first review

- `src/xr_source/cpp/grammar/__init__.py`: native C++ grammar contract data;
- `src/xr_source/cmake/grammar/node-types.json`: optional CMake grammar data;
- grammar license files: third-party attribution for CMake only;
- `tests/`: validation rather than architecture;
- `tools/`: corpus/parity utilities rather than runtime package logic.

### Core invariants

#### 1. Lossless source representation

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Diagnostics do not relax this invariant.

#### 2. Green objects never know absolute positions

A `GreenNode` can be reused at another source location without mutation.
`SyntaxNode` adds parent/index/offset information for one tree snapshot.

#### 3. C++ owns its parser

The base C++ frontend is `xr-source` code: lexer, structural parser and native
grammar contract. No Tree-sitter object exists on the C++ path.

The generic Tree-sitter adapter remains only for optional frontends such as
CMake.

#### 4. Grammar structure is data

`LanguageGrammar` describes structural contracts without forcing consumers to
depend on a parser backend. C++ populates it from its native contract; CMake
currently populates it from versioned Tree-sitter grammar metadata.

#### 5. Syntax is not semantics

The core does not perform name lookup, overload resolution, template
instantiation, type inference or constant evaluation. XRobot constructor/view
binding remains XRobot domain logic.

#### 6. Render and format are different operations

`render()` reproduces represented source. The layout IR decides how newly
generated source wraps and indents. Formatting does not normalize untouched
parsed source.

### Why edits reparse at the document level

Low-level `SyntaxTree.replace/remove/insert_*` uses persistent green-tree
rewrites and can reuse unaffected subtrees. After a high-level document edit,
the result is rendered and reparsed. This pays some performance to restore
language-owned fields, diagnostics and structural invariants.

Incremental native reparsing can be added later if profiling justifies it; it
should not weaken snapshot safety or source fidelity.

### Suggested review questions

- Can every source byte survive parse/render unchanged?
- Does any language-specific concept leak into `core/`?
- Does the C++ import path pull in a third-party parser?
- Is duplicated source state being introduced?
- Does a convenience view accidentally become an incomplete semantic AST?
- Are edits immutable and snapshot-safe?
- Is formatting kept out of XRobot/LibXR business logic?
