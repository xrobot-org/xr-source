# 架构设计

## 设计约束

1. **完整保真**：每一个源码字节都必须属于 node、token 或 trivia，不能因为 parser 不认识就静默丢弃。
2. **不可变快照**：底层结构重写只重建发生变化的祖先链；高层语言文档在编辑后重新解析，以刷新 field、诊断和错误恢复结构。
3. **C++ 前端自包含**：C++ 解析不能依赖 Tree-sitter、Clang、libclang 或其他 parser runtime。
4. **先语法、后语义**：源码结构不依赖编译器即可读取；名称解析、类型系统等语义能力另行提供。
5. **核心语言无关**：C++、CMake 以及后续语言复用同一套 tree/rewrite/layout 基础设施。
6. **解析与生成汇合**：Builder 生成的结果最终进入与已有源码解析结果相同的语法表示。
7. **render 与 format 分离**：`render()` 负责原样还原当前表示；format 只决定新生成源码如何排版。

## 参考的成熟设计

主要参考以下项目的思想，而不是逐行复刻实现：

- **Roslyn**：full-fidelity immutable node/token/trivia 模型和快照复用；
- **SwiftSyntax**：源码精确结构与编译器语义分离；
- **LibCST**：concrete syntax 与独立 metadata/provider；
- **Tree-sitter**：concrete syntax、错误恢复和增量解析设计；目前只作为 CMake 可选后端和设计参考。

## 分层

C++ 使用自有前端：

```text
consumer（XRobot / LibXR code generator）
                 |
          C++ typed views
                 |
       native C++ lexer + parser
                 |
      immutable syntax core
                 |
         rewrite / layout
```

CMake 复用同一核心，但 parser backend 可选：

```text
CMake typed views
        |
optional Tree-sitter adapter
        |
immutable syntax core
```

格式化单独存在：

```text
syntax -> language formatter -> layout document -> text
```

## Green / Red 模型

### Green

Green 元素不可变、与绝对位置无关：

- `GreenNode`：保存 children 和 field edge；
- `GreenToken`：保存叶子语法及其源码文本；
- `GreenTrivia`：保存 parser 没有暴露但必须保留的源码间隙；
- 不保存 parent；
- 不保存绝对 offset。

因此，只要某棵子树没有变化，就可以在不同不可变快照之间直接复用对象。

### Red

Red 元素绑定到一个具体 `SyntaxTree` 快照，在 green 数据之上派生：

- parent；
- child index；
- field；
- absolute byte offset；
- span。

Red path 只对所属快照有效，不能把旧快照里的 red node 当成编辑后新文档里的稳定对象身份。

## 不可变编辑

`SyntaxTree.replace/remove/insert_*` 是底层持久化编辑：

- 只重建目标到根之间的节点；
- 路径之外的 green 子树保持 identity；
- 不主动重新调用语言 parser。

`CppDocument` / `CMakeDocument` 的高层编辑会在底层操作后：

1. render 修改后的字节；
2. 用对应语言 parser 重新解析；
3. 返回新的语言文档快照。

这样做目前优先保证正确性：消费者不会看到过期的 field、diagnostics 或 error-recovery 结构。以后如有性能需要，可以在不改变 API 契约的情况下加入增量重解析。

## C++ 无损模型

Native C++ lexer 必须无损保存：

- 普通空白；
- CR / LF / CRLF；
- 注释；
- UTF-8 BOM；
- 普通和 raw string literal；
- 预处理指令；
- 标点与运算符；
- 当前尚未细分的源码片段。

硬不变量：

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

结构 parser 只会把连续 lexeme 区间替换成嵌套 green node，不会归一化对应源码文本。

即使输入不完整或 parser 给出诊断，也仍然要求逐字节还原。

## Native C++ parser 的边界

Native parser 是**source-structure parser**，不是编译器前端。

当前重点识别消费者真正需要的结构，例如：

- include / preprocessor；
- declaration / variable；
- function / constructor / special member；
- class / struct / namespace；
- template parameter；
- call / argument；
- 常见 expression；
- control flow；
- User Code / format / lint 等源码约定。

当一个结构没有语义信息就无法安全分类时，parser 应优先把它保留成 generic lossless source node，而不是猜测错误的 AST。

明确不做：

- name lookup；
- overload resolution；
- template instantiation；
- type inference；
- constant evaluation；
- 预处理配置求值。

## Parser 依赖边界

基础包：

```toml
dependencies = []
```

C++ frontend：

- 不依赖 `tree-sitter-cpp`；
- 不依赖 `tree-sitter`；
- 不打包 C++ Tree-sitter grammar JSON；
- 不经过 `xr_source.parser.tree_sitter`。

CMake 是独立 optional frontend：

```text
xr-source[cmake]
    -> tree-sitter-language-pack
    -> tree-sitter runtime
```

这个依赖链不参与 C++ 的 import / parse 路径。

## Grammar 合同

`LanguageGrammar` 是语言无关结构合同，和具体 parser runtime 对象解耦。

C++：

- grammar 合同直接维护在 `src/xr_source/cpp/grammar/__init__.py`；
- 当前身份：`xr-cpp-0.1` / `native-source-model-v1`；
- 不再存在 `cpp/grammar/node-types.json`。

CMake：

- 仍打包固定版本的 `node-types.json`；
- 加载时对规范化 UTF-8 JSON 做 checksum；
- 最终仍映射成同一个 `LanguageGrammar` 数据模型。

## 语义边界

语法核心不回答：

- identifier 最终绑定到哪个声明；
- 某个表达式实例化后的真实类型；
- 调用最终选择哪个重载；
- 某段代码在特定宏配置下是否可编译。

XRobot 的 Module constructor/view 绑定同样属于 XRobot domain logic，不应该塞进通用源码模型。
