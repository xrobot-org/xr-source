# Review guide

The fastest review path is the immutable syntax core followed by the native C++
frontend. CMake is an optional frontend and can be reviewed separately.

## Read these first

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

## Files you can mostly skip on the first review

- `src/xr_source/cpp/grammar/__init__.py`: native C++ grammar contract data;
- `src/xr_source/cmake/grammar/node-types.json`: optional CMake grammar data;
- grammar license files: third-party attribution for CMake only;
- `tests/`: validation rather than architecture;
- `tools/`: corpus/parity utilities rather than runtime package logic.

## Core invariants

### 1. Lossless source representation

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Diagnostics do not relax this invariant.

### 2. Green objects never know absolute positions

A `GreenNode` can be reused at another source location without mutation.
`SyntaxNode` adds parent/index/offset information for one tree snapshot.

### 3. C++ owns its parser

The base C++ frontend is `xr-source` code: lexer, structural parser and native
grammar contract. No Tree-sitter object exists on the C++ path.

The generic Tree-sitter adapter remains only for optional frontends such as
CMake.

### 4. Grammar structure is data

`LanguageGrammar` describes structural contracts without forcing consumers to
depend on a parser backend. C++ populates it from its native contract; CMake
currently populates it from versioned Tree-sitter grammar metadata.

### 5. Syntax is not semantics

The core does not perform name lookup, overload resolution, template
instantiation, type inference or constant evaluation. XRobot constructor/view
binding remains XRobot domain logic.

### 6. Render and format are different operations

`render()` reproduces represented source. The layout IR decides how newly
generated source wraps and indents. Formatting does not normalize untouched
parsed source.

## Why edits reparse at the document level

Low-level `SyntaxTree.replace/remove/insert_*` uses persistent green-tree
rewrites and can reuse unaffected subtrees. After a high-level document edit,
the result is rendered and reparsed. This pays some performance to restore
language-owned fields, diagnostics and structural invariants.

Incremental native reparsing can be added later if profiling justifies it; it
should not weaken snapshot safety or source fidelity.

## Suggested review questions

- Can every source byte survive parse/render unchanged?
- Does any language-specific concept leak into `core/`?
- Does the C++ import path pull in a third-party parser?
- Is duplicated source state being introduced?
- Does a convenience view accidentally become an incomplete semantic AST?
- Are edits immutable and snapshot-safe?
- Is formatting kept out of XRobot/LibXR business logic?
