# Validation status

Date: 2026-09-18.

This document records evidence for the native C++ parser transition. Source
fidelity, structural classification and compiler semantic validity are separate
properties.

## Current native-parser checks

The native C++ frontend is exercised by the package test suite on Linux and
Windows across Python 3.10, 3.12 and 3.14.

The formatter/diagnostic run used during the migration reported:

- pytest: 37/37 passed;
- Ruff: all checks passed;
- mypy strict: no issues in 38 source files;
- sdist and pure-Python wheel: build successfully;
- package metadata: sdist and wheel pass `twine check`;
- isolated base-wheel smoke test: C++ parses without installing Tree-sitter.

The normal CI workflow remains the authoritative final matrix check.

## Dependency isolation

The base package declares no runtime dependencies.

C++ specifically has:

- no `tree-sitter-cpp` dependency;
- no `tree-sitter` dependency;
- no packaged C++ Tree-sitter grammar JSON or Tree-sitter C++ license payload;
- no C++ import path through `xr_source.parser.tree_sitter`.

The package CI installs the built wheel into an environment that has only the
build/check tooling, then parses C++ and checks that no Tree-sitter module was
loaded. It also checks wheel metadata for any accidental
`tree-sitter-cpp` requirement.

CMake is intentionally separate: `xr-source[cmake]` may install
`tree-sitter-language-pack` and its Tree-sitter runtime.

## Lossless round-trip contract

The native parser asserts byte fidelity on every parse:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

Unit coverage includes CRLF, comments, preprocessor directives, raw strings,
UTF-8 BOM, empty files and malformed/incomplete source.

Before the native parser transition, the Tree-sitter-backed prototype was
stress-tested on a 4,420-file / 153,971,079-byte local ecosystem corpus with
zero round-trip failures. That historical result remains useful as the corpus
definition and fidelity baseline, but it is **not** presented as native-parser
evidence. The same corpus must be rerun against the native frontend before an
equivalent native full-corpus claim is made.

## Structural compatibility

The current tests cover the source-level interfaces required by XRobot tooling,
including:

- includes;
- classes and access sections;
- function and constructor views;
- complex parameter declarators;
- template parameters;
- deleted/defaulted special members;
- file- and block-scope variables;
- call expressions and arguments;
- modern C++ syntax categories such as lambda, requires, fold and co_await;
- immutable edits and reparsing;
- protected user/format/lint regions.

The native parser intentionally falls back to generic lossless source nodes
where classification would require semantic knowledge.

## CMake validation

CMake continues to use the optional `tree-sitter-language-pack` backend.
Its grammar metadata remains versioned under
`src/xr_source/cmake/grammar/`. CMake is tested through the same immutable
syntax/rewrite core but is not evidence for the independence of the C++
frontend.

## Historical XRobot compatibility evidence

The earlier source-model prototype compared typed constructor views with the
then-current XRobot Module parser across 66 primary Module headers:

- 64 headers accepted by the XRobot parser: 64/64 constructor
  name/type/default shapes matched;
- 2 headers were already rejected by the XRobot parser;
- 0 regressions among interfaces accepted by that baseline.

Because the C++ backend has now changed, this is historical baseline evidence.
A new native-parser parity run should replace it before declaring corpus-level
migration complete.

## Local evidence directory

Earlier corpus/parity evidence is stored under:

`D:/XRobotWork/ecosystem-20260915/evidence/xr-source-20260918/`

Important historical outputs include:

- `cpp-roundtrip-final.json`;
- `cpp-only-roundtrip.json`;
- `cmake-roundtrip.json`;
- `xrobot-interface-compare.json`.

These files are validation artifacts and are not runtime dependencies.
