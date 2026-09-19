# 架构 / Architecture

## 语法树 / Syntax Tree

底层使用不可变 green tree 保存源码内容。`GreenNode` 保存 children，`GreenToken` 保存语法 token，`GreenTrivia` 保存空白和未分类源码。green 元素不保存 parent 和绝对位置。  
The immutable green tree stores source content. `GreenNode` owns children, `GreenToken` stores syntax tokens, and `GreenTrivia` keeps whitespace and unclassified source. Green elements do not store parents or absolute positions.

red view 在具体 `SyntaxTree` 快照上补充 parent、child index、field、byte offset 和 span。  
Red views add parent, child index, field, byte offset, and span for one `SyntaxTree` snapshot.

## 无损解析 / Lossless Parsing

C++ 和 CMake 都要求：  
Both C++ and CMake keep this invariant:

```python
tree = parser.parse(source)
assert tree.render_bytes() == source
```

parser 可以识别部分结构，也可以把暂时未细分的内容保存在 token/trivia 中；无论是否产生诊断，源码字节都必须保留。  
A parser may classify only part of a file and leave other text in tokens or trivia. Diagnostics do not change the byte-preservation rule.

## 编辑 / Editing

`SyntaxTree.replace/remove/insert_*` 只重建目标到根之间的 green 节点，其余子树继续复用。  
`SyntaxTree.replace/remove/insert_*` rebuilds only the green nodes between the edited element and the root; untouched subtrees are reused.

`CppDocument` 和 `CMakeDocument` 的高层编辑会重新解析修改后的源码，让 field 和 diagnostics 与新快照保持一致。  
High-level `CppDocument` and `CMakeDocument` edits reparse the modified source so fields and diagnostics match the new snapshot.

## C++ parser

C++ frontend 由 lexer、结构 parser 和 grammar contract 组成。lexer 保留换行、注释、literal、预处理内容和标点；结构 parser 在这些 lexeme 上建立 declaration、function、class、call、expression 等节点。  
The C++ frontend consists of a lexer, structural parser, and grammar contract. The lexer preserves line endings, comments, literals, preprocessor text, and punctuation; the structural parser builds declaration, function, class, call, expression, and related nodes over those lexemes.

## CMake parser

CMake frontend 直接解析 command、argument、comment 和成对 block，例如 `if()/endif()`、`function()/endfunction()`。它与 C++ frontend 一样包含在基础包中。  
The CMake frontend directly parses commands, arguments, comments, and paired blocks such as `if()/endif()` and `function()/endfunction()`. It ships in the base package together with the C++ frontend.

## Grammar contract

`LanguageGrammar` 保存 node kind、field、children 和 subtype 关系。C++ 使用项目内维护的 native contract；CMake 使用固定版本的 grammar metadata 生成同一种结构描述。  
`LanguageGrammar` stores node kinds, fields, child rules, and subtype relationships. C++ uses a native contract maintained in this project; CMake maps pinned grammar metadata into the same representation.

## Builder 与 formatter / Builder and Formatter

Factory 和 builder 负责创建源码片段，生成后的文本重新进入 parser，因此读取和生成使用同一套语法表示。  
Factories and builders create source fragments and feed generated text back through the parser, so parsed and generated code use the same syntax representation.

layout IR 决定新生成文本的换行和缩进。已有源码的 `render()` 直接还原语法树保存的内容。  
The layout IR controls wrapping and indentation for generated text. `render()` reproduces the source stored by an existing syntax tree.

## 语义接口 / Semantic Integration

需要名称解析、类型信息或重载结果时，可以在 syntax tree 之上接编译器或项目自己的 semantic provider。  
Name resolution, type information, and overload results can be supplied by a compiler or project-specific semantic provider layered above the syntax tree.
