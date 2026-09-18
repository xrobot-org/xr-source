# Roadmap

## Milestone 0：源码核心与 Native C++ proof

已完成：

- immutable green/red syntax model；
- 自有、full-fidelity C++ lexer 与 structural parser；
- native C++ grammar contract；
- 常用 typed views；
- file/function/block builder；
- 独立 layout/format IR；
- 基础 wheel 的 C++ 路径零 parser runtime 依赖；
- Linux/Windows 多 Python 版本 CI；
- 公开真实 corpus round-trip 验证。

## Milestone 1：强化 Native C++ 表示

接下来重点：

- 在本地完整历史 ecosystem corpus 上重跑 native parser，把它升级为新的完整 fidelity baseline；
- 重新执行 XRobot Module constructor-interface parity，替换旧 Tree-sitter backend 的历史结果；
- 只根据真实 consumer/corpus 失败拓展语法分类，不为了“看起来完整”盲目堆 AST 类；
- 对 preprocessor、declarator 增加更好用的 first-class convenience API；
- 增加源码行索引和编辑后的稳定 diagnostics；
- benchmark 大型 vendored translation unit，针对真实瓶颈优化；
- 如有需求，引入独立 compiler-semantic provider，但不能反向耦合 syntax core。

## Milestone 2：迁移消费者

- 把 XRobot registration / Module interface 读取迁移到 xr-source adapter；
- 把 `xrobot_main` 生成迁移到 `CppFileBuilder`；
- 把 LibXR `app_main` 生成和 User Code 保护区域迁移过来；
- 只有在 golden-output parity 通过以后，才删除旧 regex/string-printer 路径。

## Milestone 3：继续完善 CMake frontend

CMake 已经复用同一套：

```text
core / tree / rewrite / grammar / layout
```

目前 parser backend 仍是可选 `tree-sitter-language-pack`。

后续原则：

- CMake Tree-sitter 依赖不得重新渗透进 C++；
- 只按真实 consumer 需求增加 function/macro/block convenience views；
- 不再建立第二套 rewrite engine。
