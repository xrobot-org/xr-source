# Roadmap

## Milestone 0: source core and C++ proof

- Immutable green/red syntax model.
- Full-fidelity Tree-sitter adapter.
- C++ generic syntax schema and common views.
- Structured builders for files/functions/blocks.
- Separate layout/format document IR.
- Real XRobot ecosystem round-trip and Module-constructor compatibility evidence.

## Milestone 1: harden C++ representation

- Evaluate the newer language-pack C++ revision (`8b5b49e…`, including C++26 reflection/splice syntax) against the same full ecosystem corpus before changing the default parser provider.
- Generate additional typed convenience wrappers from the packaged C++ grammar schema instead of hand-writing a large AST.
- Add first-class preprocessor and declarator conveniences.
- Add source-line indexing and stable diagnostics after incremental edits.
- Benchmark and optimize large vendored translation units.
- Add optional compiler-semantic provider without coupling it to the syntax core.

## Milestone 2: consumer migration

- Migrate XRobot registration and Module interface reads behind xr-source adapters.
- Migrate xrobot_main generation to CppFileBuilder.
- Migrate LibXR app_main generation and protected user regions.
- Remove duplicated regex/string-printer paths only after golden-output parity.

## Milestone 3: CMake frontend

Initial frontend implemented on the same core/tree/rewrite/layout layers.
It is an optional extra backed by `tree-sitter-language-pack 1.20.0`, which
ships cross-platform binary wheels and has been verified with the package's
pinned Tree-sitter 0.25.2 runtime. The direct
`tree-sitter-cmake` package is deliberately not a base dependency because its
published metadata targets Tree-sitter 0.24 and source installation may require
a local Python development toolchain. Harden block/function/macro convenience
views only as real consumers require them; do not introduce a second rewrite
engine.
