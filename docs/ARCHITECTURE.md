# Architecture

## Design constraints

1. Full fidelity: every source byte is represented by syntax, token or trivia.
2. Immutable snapshots: structural core rewrites rebuild only the changed ancestor chain. Language documents currently reparse the rewritten bytes to restore parser-owned fields and diagnostics; incremental reparse/reuse is a later optimization, not a current API promise.
3. Parser isolation: Tree-sitter is an implementation detail, not the public syntax API.
4. Syntax before semantics: source structure is available without a compiler invocation.
5. Generic core: C++ and future CMake frontends share tree/rewrite/layout infrastructure.
6. Builders create the same syntax representation returned by parsing.
7. render preserves source; formatting is a separate operation.

## Mature designs used as references

- Roslyn syntax trees: full-fidelity immutable node/token/trivia model and snapshot reuse.
  https://github.com/dotnet/roslyn/blob/main/docs/wiki/Roslyn-Overview.md
- SwiftSyntax: source-accurate traversal distinct from fixed-up structural views.
  https://github.com/swiftlang/swift-syntax
- LibCST: concrete syntax plus independent metadata providers.
  https://libcst.readthedocs.io/
- Tree-sitter: robust concrete syntax parsing and incremental parsing.
  https://tree-sitter.github.io/tree-sitter/

These projects are references for separation of concerns. xr-source does not
mirror any one implementation one-for-one.

## Layers

    consumer (XRobot / LibXR code generator)
                  |
          language conveniences
                  |
           C++ syntax frontend
                  |
      immutable syntax core + rewrite
                  |
           parser adapter
                  |
              Tree-sitter

Formatting is separate:

    syntax -> language formatter -> layout document -> text

## Green and red views

Green elements are immutable and position-independent. A green node contains
children but no parent pointer or absolute source offset. Red elements are cheap
views over a green tree and add parent, child index, field name and absolute byte
offset.

The low-level `SyntaxTree` rewrite API rebuilds only the ancestor chain of the changed element and reuses untouched green elements. High-level `CppDocument`/`CMakeDocument` edits then reparse the resulting bytes so parser-owned field labels and diagnostics cannot become stale. Incremental Tree-sitter edit reuse is intentionally deferred until its correctness contract is covered by tests.

## Fidelity

Tree-sitter omits whitespace from its syntax children. The parser adapter fills
every byte gap between syntax children with GreenTrivia. Rendering the root is
therefore a concatenation of all represented source text, including CRLF,
comments, directives, unusual spacing and malformed/incomplete input.

## Parser compatibility

The default C++ backend intentionally pins `tree-sitter 0.25.2` with the
official `tree-sitter-cpp 0.23.4` Python grammar package. The combination of
`tree-sitter 0.26.0` and that grammar wheel reproducibly caused a native
SIGSEGV on a real STM32 source (`system_stm32f4xx.c`, 26,695 bytes), while the
0.25.2 combination parsed the same bytes and round-tripped them exactly. A
separate control using the C++ grammar distributed inside
`tree-sitter-language-pack 1.20.0` did not crash under Tree-sitter 0.26.0, so
this is recorded as a backend-combination compatibility problem rather than a
claim that the 0.26 runtime is universally broken. The language-pack C++
grammar did not improve the known syntax diagnostics in the generated
`xrobot_main.hpp`, and changing the default grammar distribution is therefore
deferred instead of being bundled with the runtime upgrade. The optional CMake
frontend is already verified with language-pack 1.20.0 on the pinned 0.25.2
runtime.

## Grammar metadata

Language syntax contracts are packaged as versioned `node-types.json` data and
loaded into the language-neutral `LanguageGrammar` model. This keeps the public
representation independent of Tree-sitter Python objects while avoiding a
hand-written hierarchy of hundreds of node classes.

Current packaged schemas:

- C++: tree-sitter-cpp v0.23.4, revision
  `f41e1a044c8a84ea9fa8577fdd2eab92ec96de02`, 407 node specifications.
- CMake: tree-sitter-cmake v0.7.4, revision
  `ca627bb5828616b6246aafdc3c3222789e728e37`, 71 node specifications. This is
  the exact revision selected by tree-sitter-language-pack 1.20.0.

The language-pack 1.20.0 C++ grammar is newer than the current PyPI
`tree-sitter-cpp` release: it points at revision
`8b5b49eb196bec7040441bee33b2c9a4838d6967`, whose schema has 430 entries and
includes C++26 reflection/splice forms such as `reflect_expression` and
`splice_expression`. It is a candidate default backend, but is not selected in
this milestone because the current official-package backend already has a
153 MB ecosystem round-trip proof and the newer provider has not yet been run
through an equivalent full-corpus A/B test.

## Semantics

The core deliberately does not answer questions such as:

- what declaration an identifier refers to;
- the instantiated type of an expression;
- which overload is selected;
- whether a program is valid after preprocessing.

Those belong to optional semantic providers or to consumer-specific models such
as XRobot constructor/view binding.
