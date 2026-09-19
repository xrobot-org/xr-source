# 验证 / Validation

## CI

CI 在 Linux 和 Windows 上运行测试，并覆盖 Python 3.8、3.10、3.12 和 3.14。  
CI runs on Linux and Windows with Python 3.8, 3.10, 3.12, and 3.14.

质量检查包括 Ruff、mypy、双语文档检查和 wheel/sdist 打包测试。  
Quality checks include Ruff, mypy, bilingual documentation checks, and wheel/sdist packaging tests.

## C++ round-trip corpus

当前 native C++ parser 已验证的公开 corpus：  
Current public corpus validated with the native C++ parser:

- 1,850 files
- 16,624,085 bytes
- 0 round-trip failures
- 4 files with parser diagnostics / 7 diagnostics

核心检查 / Core check:

```python
tree = CppParser().parse(source)
assert tree.render_bytes() == source
```

真实 corpus 曾发现 expression replacement 吞掉边缘 trivia 的问题，修复后加入了回归测试。  
The real corpus exposed an expression-replacement bug that consumed edge trivia; the fix is covered by a regression test.

## CMake

CMake parser 已并入基础包，测试覆盖 CRLF round-trip、命令查询、builder 和结构化编辑。  
The CMake parser ships in the base package, with tests for CRLF round trips, command queries, builders, and structured edits.

## 历史基线 / Historical Baselines

旧 Tree-sitter C++ backend 曾跑过 4,420 files / 153,971,079 bytes 的 corpus；该结果只作为历史基线，不代表当前 native parser 的覆盖数字。  
The former Tree-sitter C++ backend ran a 4,420-file / 153,971,079-byte corpus. That result is kept as a historical baseline and is not counted as native-parser coverage.

旧 XRobot constructor parity 结果为 64/64；native backend 仍需要重新跑完整 parity。  
The previous XRobot constructor-parity result was 64/64; the complete parity run still needs to be repeated with the native backend.

## 性能基线 / Performance Baseline

进入 consumer migration 前使用同一个脚本记录 parse、query、单次编辑和批量编辑耗时：  
Use the same script before consumer migration to record parse, query, single-edit, and repeated-edit costs:

```bash
PYTHONPATH=src python tools/benchmark_source_model.py --sizes 10000 100000 1000000 --batch-edits 3
```

结果按 TSV 输出。基准只用于比较同一机器上的版本变化，不作为跨机器性能指标。  
Results are emitted as TSV. Use them to compare revisions on the same machine rather than as cross-machine performance numbers.

批量高层编辑会重复完整解析；迁移 consumer 时应优先合并修改后一次 reparse。  
Repeated high-level edits trigger repeated full reparses; consumer migrations should batch changes before reparsing when possible.
