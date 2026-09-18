# Architecture

## Design constraints

1. Full fidelity: every source byte is represented by syntax, token or trivia.
2. Immutable snapshots: low-level structural rewrites rebuild only the changed ancestor chain. Language documents reparse rewritten bytes so fields and diagnostics stay synchronized.
3. Self-contained C++ frontend: C++ parsing must not require Tree-sitter, Clang, libclang, or another parser runtime.
4. Syntax before semantics: source structure is available without a compiler invocation.
5. Generic core: C++, CMake, and future frontends share tree/rewrite/layout infrastructure.
6. Builders create the same syntax representation returned by parsing.
7. `render()` preserves represented source; formatting is a separate operation.

## Mature designs used as references

- Roslyn syntax trees: full-fidelity immutable node/token/trivia model and snapshot reuse.
- SwiftSyntax: source-accurate traversal distinct from compiler semantics.
- LibCST: concrete syntax plus independent metadata/providers.
- Tree-sitter: useful reference for concrete syntax and incremental parsing; it remains an optional implementation detail for the CMake frontend only.

These projects are design references. `xr-source` does not mirror one implementation one-for-one.

## Layers

C++ uses the native frontend:

```text
consumer (XRobot / LibXR code generator)
                 |
         C++ convenience views
                 |
       native C++ lexer + parser
                 |
     immutable syntax core + rewrite
```

CMake reuses the same core through an optional backend:

```text
CMake convenience views
         |
optional Tree-sitter adapter
         |
immutable syntax core + rewrite
```

Formatting is separate:

```text
syntax -> language formatter -> layout document -> text
```

## Green and red views

Green elements are immutable and position-independent. A green node contains
children but no parent pointer or absolute source offset. Red elements are
snapshot-specific views that add parent, child index, field name and absolute
byte offset.

The low-level `SyntaxTree` rewrite API rebuilds only the ancestor chain of the
changed element and reuses untouched green elements. High-level
`CppDocument`/`CMakeDocument` edits render and reparse the changed source so
parser-owned fields and diagnostics cannot become stale.

## C++ fidelity model

The native C++ lexer is lossless. Whitespace, CR/LF/CRLF, comments, BOMs,
directives, literals, punctuation and otherwise-unclassified source all remain
represented in source order. The structural parser replaces selected lexeme
ranges with nested green nodes without normalizing their text.

The hard invariant is:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Malformed or incomplete C++ can therefore carry diagnostics while remaining
byte-identical on render.

## Native C++ parser boundary

The parser is intentionally a source-structure parser, not a compiler frontend.
It recognizes the structures needed by `xr-source` consumers, including common
declarations, functions, classes, templates, calls, expressions, control flow,
preprocessor directives and protected-source patterns.

When a construct cannot be safely classified without semantic information, the
parser keeps the source losslessly under a generic source node instead of
guessing compiler semantics.

It does not perform:

- name lookup;
- overload resolution;
- template instantiation;
- type inference;
- constant evaluation;
- preprocessing configuration evaluation.

Those belong to a compiler/semantic provider or to consumer-specific models.

## Parser dependencies

The base package has no runtime dependencies. In particular, the C++ frontend
does not import or package `tree-sitter-cpp`, and it does not require the
`tree-sitter` Python package.

CMake remains an optional frontend. Installing `xr-source[cmake]` currently
uses `tree-sitter-language-pack` and the generic
`xr_source.parser.tree_sitter` adapter. That optional dependency path is
separate from C++.

## Grammar metadata

Both frontends expose the language-neutral `LanguageGrammar` API, but their
metadata sources differ.

C++ grammar contracts are maintained by `xr-source` itself in
`src/xr_source/cpp/grammar/__init__.py`. The current native contract is
`xr-cpp-0.1` / `native-source-model-v1`. There is no packaged
`cpp/grammar/node-types.json` and no C++ grammar file copied from
Tree-sitter.

CMake still packages the versioned `node-types.json` corresponding to its
optional Tree-sitter grammar and maps it into the same `LanguageGrammar`
representation.

## Semantics

The syntax core deliberately does not answer questions such as which declaration
an identifier refers to or which overload will be selected. XRobot
constructor/view binding likewise remains XRobot domain logic rather than being
embedded in `xr-source`.
