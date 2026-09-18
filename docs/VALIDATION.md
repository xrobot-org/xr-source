# Validation status

Date: 2026-09-18.

This document records evidence for the current source-model milestone. It is not
a claim that Tree-sitter semantically accepts every compiler extension or every
preprocessor configuration.

## Unit and static checks

- pytest: 35/35 on Python 3.12.3.
- Python 3.10.21: 35/35.
- Python 3.14.7: 35/35.
- mypy strict: no issues in the package sources.
- ruff: required clean before the milestone commit.
- package: sdist and pure-Python wheel build successfully.
- package metadata: both artifacts pass `twine check`.
- isolated wheel install: C++ and optional CMake frontends import and parse real
  DevC fixtures.

## Lossless round-trip

The parser invariant is byte fidelity, independently of parser diagnostics.

Full ecosystem stress test, including C, C++, headers and vendored STM32/CMSIS/
Eigen sources:

- 4,420 files.
- 153,971,079 bytes.
- 0 round-trip failures.
- 1,866 files contain Tree-sitter diagnostics; 83,250 diagnostics total.

C++-family subset (`.cpp/.hpp/.cc/.cxx/.hh/.hxx`):

- 1,451 files.
- 9,461,521 bytes.
- 0 round-trip failures.
- 571 files contain Tree-sitter diagnostics; 2,403 diagnostics total.

The diagnostic count is deliberately reported rather than hidden. Full-fidelity
source representation and full grammar acceptance are separate properties.

CMake ecosystem test:

- 248 `CMakeLists.txt` / `.cmake` files.
- 524,091 bytes.
- 0 diagnostics.
- 0 round-trip failures.

## XRobot compatibility

The new typed C++ constructor view was compared against the current XRobot
Module parser across 66 primary Module headers:

- 64 headers accepted by the current XRobot parser: 64/64 constructor parameter
  name/type/default shapes match.
- 2 headers are already rejected by the current XRobot parser
  (`QDU-Robomaster/Motor` and `xrobot-org/DurationStatistics`).
- 0 regressions among the interfaces XRobot currently accepts.

Real DevC source inspection through the new API:

- `app_main.cpp`: one `app_main`, 41 `XR_REGISTER` calls, 119 variable
  declarations classified by convenience views, three user regions, two
  clang-format regions and two NOLINT regions.
- `xrobot_main.hpp`: one `XRobotMain`; byte-identical round-trip.
- Both files render byte-for-byte identical to their inputs.

## Parser backend compatibility

The default C++ backend is pinned to:

- `tree-sitter 0.25.2`
- `tree-sitter-cpp 0.23.4` (revision
  `f41e1a044c8a84ea9fa8577fdd2eab92ec96de02`)

A real STM32 source, `system_stm32f4xx.c` (26,695 bytes), reproducibly caused
a native SIGSEGV with the combination `tree-sitter 0.26.0` +
`tree-sitter-cpp 0.23.4`. The pinned 0.25.2 combination round-trips the same
file exactly.

A separate control using the C++ grammar bundled by
`tree-sitter-language-pack 1.20.0` does not crash under runtime 0.26.0, so
the finding is a backend-combination compatibility issue, not a claim that
Tree-sitter 0.26.0 is universally broken.

CMake uses the optional `tree-sitter-language-pack 1.20.0` grammar and is
verified with the same pinned 0.25.2 runtime. The language-pack source lock
identifies `uyha/tree-sitter-cmake` revision
`ca627bb5828616b6246aafdc3c3222789e728e37` (v0.7.4); the packaged CMake
`node-types.json` is taken from that exact revision and all node/type references
match the runtime language schema.

## Grammar schemas

The package ships versioned, checksummed grammar metadata rather than a
hand-maintained list of syntax forms:

- C++: 407 node specifications from tree-sitter-cpp v0.23.4; 98 node kinds
  declare named fields, 111 declare generic children, and 7 are abstract
  subtype sets. The `expression` subtype set includes lambda, requires, fold,
  coroutine await, call, new, binary and the other grammar-defined expression
  forms.
- CMake: 71 node specifications from tree-sitter-cmake v0.7.4.

Both frontends expose these through the same `LanguageGrammar` data model. A
syntax node can be mapped back to its grammar contract with
`document.grammar_spec(node)`; C++ additionally exposes grammar-driven
`is_expression()` and `is_statement()` helpers.

## Evidence files

The local evidence directory is:

`D:/XRobotWork/ecosystem-20260915/evidence/xr-source-20260918/`

Important machine-readable outputs:

- `cpp-roundtrip-final.json`
- `cpp-only-roundtrip.json`
- `cmake-roundtrip.json`
- `xrobot-interface-compare.json`

The package itself does not depend on those evidence files at runtime.
