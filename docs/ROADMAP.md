# 路线图 / Roadmap

## 近期 / Near Term

- 扩充 C++ expression、declarator 和 preprocessor 的结构覆盖。  
  Expand structural coverage for C++ expressions, declarators, and preprocessor constructs.

- 扩充 CMake command/argument/block 的真实工程 corpus。  
  Expand the real-project corpus for CMake commands, arguments, and blocks.

- 在 XRobot 和 LibXR 的实际生成流程中替换字符串拼接和临时 parser。  
  Replace ad-hoc string assembly and temporary parsers in XRobot and LibXR generation flows.

- 重新跑历史大 C++ corpus；XRobot 官方模块 constructor parity 已完成 28/28（另 1 个模块无 manifest）。  
  Rerun the historical large C++ corpus; official XRobot constructor parity is complete at 28/28, with one module skipped because it has no manifest.

## 后续 / Later

- 增量 reparse 与性能优化。  
  Incremental reparsing and performance work.

- 更完整的 source-level C++ typed views。  
  Broader source-level typed views for C++.

- 按需要接入独立 semantic provider。  
  Add an independent semantic provider when a consumer needs compiler-level information.
