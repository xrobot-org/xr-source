"""比较 xr-source 与旧 XRobot ModuleParser 对模块构造函数接口的解析结果。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from xrobot.ModuleParser import source_interface

from xr_source.cpp import CppDocument


def normalized(value: str | None) -> str | None:
    """规范化类型/默认值文本中的空白和常见标点间距，便于接口结果比较。"""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value.strip())
    text = re.sub(r"\s*([*&<>,()[\]])\s*", r"\1", text)
    text = re.sub(r"\s*::\s*", "::", text)
    return text


def main() -> None:
    """解析命令行参数并执行当前工具的完整验证流程。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("modules", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    mismatches: list[dict[str, object]] = []
    for owner in sorted(path for path in args.modules.iterdir() if path.is_dir()):
        for module in sorted(path for path in owner.iterdir() if path.is_dir()):
            header = module / f"{module.name}.hpp"
            if not header.is_file():
                continue
            try:
                legacy = source_interface(header)
            except Exception as error:
                rows.append(
                    {
                        "module": f"{owner.name}/{module.name}",
                        "status": "legacy-rejected",
                        "error": repr(error),
                    }
                )
                continue

            document = CppDocument.parse(header.read_bytes(), source_name=str(header))
            classes = document.class_views(legacy["name"])
            if len(classes) != 1:
                mismatch = {
                    "module": f"{owner.name}/{module.name}",
                    "reason": "class-count",
                    "legacy_name": legacy["name"],
                    "new_count": len(classes),
                }
                mismatches.append(mismatch)
                rows.append({**mismatch, "status": "mismatch"})
                continue

            constructors = classes[0].constructors(
                public_only=True,
                callable_only=True,
            )
            legacy_constructors = legacy["constructors"]
            entry: dict[str, object] = {
                "module": f"{owner.name}/{module.name}",
                "diagnostics": len(document.diagnostics),
                "legacy_constructors": len(legacy_constructors),
                "new_constructors": len(constructors),
            }
            if len(constructors) != len(legacy_constructors):
                entry["status"] = "mismatch"
                entry["reason"] = "constructor-count"
                mismatches.append(dict(entry))
                rows.append(entry)
                continue

            constructor_rows: list[dict[str, object]] = []
            constructor_ok = True
            for index, (old, new) in enumerate(
                zip(legacy_constructors, constructors, strict=False)
            ):
                old_args = old["arguments"]
                new_args = new.parameters
                params = []
                if len(old_args) != len(new_args):
                    constructor_ok = False
                for old_arg, new_arg in zip(old_args, new_args, strict=False):
                    old_tuple = (
                        old_arg["name"],
                        normalized(old_arg["type"]),
                        normalized(old_arg["default"]),
                    )
                    new_tuple = (
                        new_arg.name,
                        normalized(new_arg.type),
                        normalized(new_arg.default),
                    )
                    equal = old_tuple == new_tuple
                    constructor_ok &= equal
                    params.append(
                        {
                            "legacy": old_tuple,
                            "new": new_tuple,
                            "equal": equal,
                        }
                    )
                constructor_rows.append(
                    {
                        "index": index,
                        "legacy_parameters": len(old_args),
                        "new_parameters": len(new_args),
                        "parameters": params,
                    }
                )
            entry["constructors"] = constructor_rows
            entry["status"] = "match" if constructor_ok else "mismatch"
            if not constructor_ok:
                entry["reason"] = "parameter-shape"
                mismatches.append(dict(entry))
            rows.append(entry)

    result = {
        "primary_headers": len(rows),
        "matches": sum(row["status"] == "match" for row in rows),
        "mismatches": len(mismatches),
        "legacy_rejected": sum(row["status"] == "legacy-rejected" for row in rows),
        "rows": rows,
        "mismatch_rows": mismatches,
    }
    print(
        f"primary_headers={result['primary_headers']} matches={result['matches']} "
        f"mismatches={result['mismatches']} legacy_rejected={result['legacy_rejected']}"
    )
    for mismatch in mismatches[:20]:
        print("MISMATCH", mismatch["module"], mismatch.get("reason"))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    raise SystemExit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
