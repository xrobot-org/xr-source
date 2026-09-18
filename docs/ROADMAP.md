# Roadmap

## Milestone 0: source core and native C++ proof

- Immutable green/red syntax model.
- Self-contained, full-fidelity C++ lexer and structural parser.
- Native C++ grammar contract and common typed views.
- Structured builders for files/functions/blocks.
- Separate layout/format document IR.
- Base wheel with no C++ parser runtime dependency.

## Milestone 1: harden native C++ representation

- Rerun the full historical ecosystem corpus against the native parser and make
  the native results the new fidelity baseline.
- Rerun XRobot Module constructor-interface parity against the native parser.
- Expand syntax classification only from concrete consumer/corpus failures;
  preserve generic lossless fallback for ambiguous constructs.
- Add first-class preprocessor and declarator conveniences where consumers need
  them.
- Add source-line indexing and stable diagnostics after incremental edits.
- Benchmark and optimize large vendored translation units.
- Add an optional compiler-semantic provider without coupling it to the syntax
  core.

## Milestone 2: consumer migration

- Migrate XRobot registration and Module interface reads behind xr-source
  adapters.
- Migrate xrobot_main generation to `CppFileBuilder`.
- Migrate LibXR app_main generation and protected user regions.
- Remove duplicated regex/string-printer paths only after golden-output parity.

## Milestone 3: CMake frontend

The initial CMake frontend is implemented on the same
core/tree/rewrite/layout layers. It remains an optional extra backed by
`tree-sitter-language-pack`.

Tree-sitter in this optional frontend is not a dependency of the native C++
frontend. Harden CMake block/function/macro convenience views only as real
consumers require them; do not introduce a second rewrite engine.
