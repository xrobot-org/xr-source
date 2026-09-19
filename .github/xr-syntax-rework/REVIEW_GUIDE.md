# 审核顺序 / Review Guide

建议先看数据模型，再看 parser，最后看高层 API 和测试。  
Review the data model first, then the parsers, followed by high-level APIs and tests.

## 1. Core

1. `src/xr_syntax/core/green.py`  
   看 green node/token/trivia 如何覆盖源码，以及不可变 replace/insert/remove。  
   Check how green nodes, tokens, and trivia cover source text and how immutable replace/insert/remove works.

2. `src/xr_syntax/core/red.py`  
   看 parent、field、index 和 byte offset 如何从 green tree 派生。  
   Check how parent, field, index, and byte offset are derived from the green tree.

3. `src/xr_syntax/core/tree.py`  
   看底层编辑是否只重建 ancestor path。  
   Check that low-level edits rebuild only the ancestor path.

4. `src/xr_syntax/core/document.py`  
   看高层编辑后的 reparse 和 snapshot 行为。  
   Check reparsing and snapshot behavior after high-level edits.

5. `src/xr_syntax/core/grammar.py`  
   看语言无关 grammar contract。  
   Review the language-neutral grammar contract.

## 2. C++

6. `src/xr_syntax/cpp/lexer.py`  
   重点检查 string/raw string、comment、CRLF、预处理和 punctuator。  
   Focus on strings/raw strings, comments, CRLF, preprocessor text, and punctuators.

7. `src/xr_syntax/cpp/parser.py`  
   看 translation unit、scope、class、namespace、template 和 preprocessor 的入口。  
   Review translation-unit, scope, class, namespace, template, and preprocessor orchestration.

8. `src/xr_syntax/cpp/_ranges.py` → `_declarator.py` → `_declaration.py` → `_expression.py`  
   先看范围和 delimiter，再看声明与表达式。`_expression_replacement()` 需要重点检查 trivia 边界。  
   Review ranges and delimiters first, then declarations and expressions. Pay particular attention to trivia boundaries in `_expression_replacement()`.

9. `src/xr_syntax/cpp/document.py` 与 `view.py`  
   看查询和 typed view 的 API。  
   Review query and typed-view APIs.

10. `src/xr_syntax/cpp/factory.py` 与 `builder.py`  
    确认生成结果回到同一 parser/model。  
    Confirm generated source returns to the same parser and model.

## 3. CMake

11. `src/xr_syntax/cmake/parser.py`  
    看 command、argument、comment、bracket argument 和 block 配对。  
    Review commands, arguments, comments, bracket arguments, and block pairing.

12. `src/xr_syntax/cmake/document.py`、`view.py`、`factory.py`、`builder.py`  
    看 CMake 查询、编辑和生成接口。  
    Review CMake query, edit, and generation APIs.

## 4. Format 与验证 / Format and Validation

13. `src/xr_syntax/format/document.py`  
    看 `Text / Line / Group / Indent / IfBreak` 和 `_fits()`。  
    Review `Text / Line / Group / Indent / IfBreak` and `_fits()`.

14. `tests/`  
    先看 round-trip 和 rewrite，再看 query、view、builder、CMake 和 package tests。  
    Start with round-trip and rewrite tests, then query, view, builder, CMake, and package tests.

审核时建议一直检查四件事：源码是否完整保留；编辑是否保持 snapshot 隔离；parser 未细分的内容是否仍能还原；生成和解析是否最终使用同一模型。  
Keep four questions in mind during review: is source preserved, are snapshots isolated after edits, can unclassified syntax still round-trip, and do parsing and generation converge on the same model?
