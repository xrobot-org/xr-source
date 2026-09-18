# Review guide

This package has 60+ tracked files because grammar metadata, tests and two language
frontends are kept separate. You do **not** need to read every file to review the
architecture.

## Read these first

1. `src/xr_source/core/green.py`
   - immutable, position-independent syntax storage;
   - every source byte ultimately belongs to a node, token or trivia object.

2. `src/xr_source/core/red.py`
   - parent/field/offset views layered over green storage;
   - positions are derived, not stored in green nodes.

3. `src/xr_source/core/grammar.py`
   - language-neutral model for Tree-sitter `node-types.json`;
   - this is the structural grammar contract used by both C++ and CMake.

4. `src/xr_source/parser/tree_sitter.py`
   - the only Tree-sitter-to-xr-source adapter;
   - fills parser byte gaps with trivia and enforces the lossless render invariant.

5. `src/xr_source/core/document.py`
   - immutable document editing facade;
   - high-level edits are reparsed so parser-owned fields/diagnostics cannot become stale.

6. `src/xr_source/cpp/document.py`
   - C++ queries and protected source regions;
   - deliberately contains no XRobot-specific semantics.

7. `src/xr_source/cpp/view.py`
   - convenience views for common C++ concepts such as functions, constructors,
     variables and calls;
   - these are wrappers over the complete syntax tree, not a second AST.

8. `src/xr_source/cpp/builder.py`
   - structured creation of files/functions/blocks using the same syntax model
     returned by parsing.

Then read `src/xr_source/format/document.py` if you want to review formatting,
and the `cmake/` directory if you want to verify that the core is actually
language-neutral.

## Files you can mostly skip on the first review

- `cpp/grammar/node-types.json` and `cmake/grammar/node-types.json`:
  upstream grammar metadata, checksummed and version-pinned.
- grammar LICENSE files: required third-party attribution.
- `tests/`: important for verification, but not required to understand the design.
- `tools/`: corpus/parity verification utilities, not runtime package logic.
- package `__init__.py` files: public exports only.

## Core invariants

### 1. Lossless source representation

For accepted input bytes:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

This remains true even when Tree-sitter emits diagnostics. Grammar acceptance and
source fidelity are separate properties.

### 2. Green objects never know absolute positions

A `GreenNode` can be reused at another source location without mutation.
`SyntaxNode` (the red view) adds parent/index/offset information for one tree
snapshot.

### 3. Tree-sitter is not the public data model

Consumers depend on `SyntaxNode`, `LanguageGrammar`, and language views.
Tree-sitter `Node` objects do not escape the parser adapter.

### 4. Grammar structure is data, not handwritten Python class sprawl

The full C++ and CMake structural contracts come from version-pinned
`node-types.json`. Common APIs such as `CppFunctionView` are convenience
wrappers only.

### 5. Syntax is not semantics

The core does not perform name lookup, overload resolution, template
instantiation, type inference or constant evaluation. XRobot constructor/view
binding remains XRobot domain logic.

### 6. Render and format are different operations

`render()` reproduces represented source.
The layout IR in `format/document.py` decides how newly generated source should
wrap/indent. Formatting never needs to rewrite untouched parsed source.

## Why edits reparse at the document level

Low-level `SyntaxTree.replace/remove/insert_*` uses persistent green-tree
rewrites and can reuse unaffected subtrees. After a high-level document edit,
the result is rendered and reparsed. This intentionally pays some performance
to restore parser-owned field labels, diagnostics and language invariants.

Incremental Tree-sitter edit/reparse is a later optimization. It should not be
added until its snapshot/stale-node contract is tested.

## C++ convenience layer boundary

`CppDocument` and `Cpp*View` may answer source-structural questions:

- where is a class/function/call;
- what text is a parameter/default expression;
- which declarations occur at translation-unit vs function scope;
- whether a method is syntactically `= delete` or `= default`.

They must not answer semantic compiler questions such as “which overload will
be called?” without an optional semantic provider.

## Suggested review questions

- Can every source byte survive parse/render unchanged?
- Does any language-specific concept leak into `core/`?
- Does any Tree-sitter object leak above `parser/`?
- Is duplicated source state being introduced?
- Does a convenience view accidentally become an incomplete replacement AST?
- Are edits immutable and snapshot-safe?
- Is formatting kept out of XRobot/LibXR business logic?
