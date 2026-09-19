from __future__ import print_function

import ast
import re
import shutil
from pathlib import Path

ROOT = Path('.')
SRC_OLD = ROOT / 'src' / 'xr_source'
SRC_NEW = ROOT / 'src' / 'xr_syntax'
CHINESE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
ENGLISH = re.compile(r'[A-Za-z]')


def rename_package():
    if SRC_NEW.exists():
        shutil.rmtree(str(SRC_NEW))
    if SRC_OLD.exists():
        SRC_OLD.rename(SRC_NEW)
    parser_dir = SRC_NEW / 'parser'
    if parser_dir.exists():
        shutil.rmtree(str(parser_dir))


def replace_names():
    for root in ('src', 'tests', 'tools'):
        for path in (ROOT / root).rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            text = text.replace('xr_source', 'xr_syntax').replace('xr-source', 'xr-syntax')
            path.write_text(text, encoding='utf-8')


def py38_compat():
    for root in ('src', 'tests', 'tools'):
        for path in (ROOT / root).rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            text = text.replace(', slots=True', '').replace('slots=True, ', '').replace('@dataclass(slots=True)', '@dataclass')
            text = text.replace('from typing import TypeAlias', 'from typing import Union')
            text = text.replace('GreenElement: TypeAlias = "GreenNode | GreenToken | GreenTrivia"', 'GreenElement = Union["GreenNode", "GreenToken", "GreenTrivia"]')
            text = text.replace('zip(legacy_constructors, constructors, strict=False)', 'zip(legacy_constructors, constructors)')
            text = text.replace('zip(old_args, new_args, strict=False)', 'zip(old_args, new_args)')
            text = text.replace('self.node.kind.removesuffix("_command")', '(self.node.kind[:-8] if self.node.kind.endswith("_command") else self.node.kind)')
            path.write_text(text, encoding='utf-8')

    for rel in ('tests/test_cpp_grammar_schema.py', 'tests/test_cmake.py'):
        path = ROOT / rel
        text = path.read_text(encoding='utf-8')
        if 'from __future__ import annotations' not in text:
            lines = text.splitlines(True)
            insert = 0
            if lines and lines[0].lstrip().startswith(('"""', "'''")):
                quote = lines[0].lstrip()[:3]
                if lines[0].count(quote) >= 2:
                    insert = 1
                else:
                    for i in range(1, len(lines)):
                        if quote in lines[i]:
                            insert = i + 1
                            break
            lines.insert(insert, '\nfrom __future__ import annotations\n')
            path.write_text(''.join(lines), encoding='utf-8')


def compact_docstrings(path):
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    edits = []

    def walk(node):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, 'body', None)
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), (ast.Str, ast.Constant)):
                value = body[0].value
                raw = value.s if isinstance(value, ast.Str) else value.value
                if isinstance(raw, str):
                    paras = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', raw.strip()) if p.strip()]
                    zh = next((p for p in paras if CHINESE.search(p)), '')
                    en = next((p for p in paras if not CHINESE.search(p) and ENGLISH.search(p)), '')
                    if not en:
                        lines = [x.strip() for x in raw.splitlines() if x.strip()]
                        en = next((x for x in lines if not CHINESE.search(x) and ENGLISH.search(x)), '')
                    if zh and en:
                        indent = ' ' * body[0].col_offset
                        new = '"""' + zh + '\n' + indent + en + '\n' + indent + '"""'
                        start = _offset(source, body[0].lineno, body[0].col_offset)
                        end = _offset(source, body[0].end_lineno, body[0].end_col_offset)
                        edits.append((start, end, new))
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(tree)
    for start, end, new in sorted(edits, reverse=True):
        source = source[:start] + new + source[end:]
    path.write_text(source, encoding='utf-8')


def _offset(source, line, col):
    lines = source.splitlines(True)
    return sum(len(x) for x in lines[:line - 1]) + col


def clean_docs_and_comments():
    for root in ('src', 'tests', 'tools'):
        for path in (ROOT / root).rglob('*.py'):
            compact_docstrings(path)
            text = path.read_text(encoding='utf-8')
            text = re.sub(r'(?m)^(\s*)# EN:\s?', r'\1# ', text)
            lines = text.splitlines(True)
            out = []
            for line in lines:
                if out and line.strip().startswith('#') and line.strip() == out[-1].strip():
                    continue
                out.append(line)
            path.write_text(''.join(out), encoding='utf-8')


def targeted_cleanup():
    changes = {
        'src/xr_syntax/core/red.py': {
            'Wrap literal text as a layout document.': 'Return the exact source text represented by this syntax element.',
            'Return the source spelling of this path.': 'Return the snapshot-local structural path as child indices.',
        },
        'src/xr_syntax/cmake/view.py': {
            'Wrap literal text as a layout document.': 'Return the exact source text of this CMake argument.',
        },
        'src/xr_syntax/cpp/view.py': {
            'Return the source spelling of this path.': 'Return the source spelling of the include path field.',
        },
    }
    for rel, mapping in changes.items():
        path = ROOT / rel
        text = path.read_text(encoding='utf-8')
        for old, new in mapping.items():
            text = text.replace(old, new)
        text = text.replace('返回该函数参数的完整源码文本。\n        Wrap literal text as a layout document.', '返回该函数参数的完整源码文本。\n        Return the complete source text of this function parameter.')
        text = text.replace('返回该模板参数的完整源码文本。\n        Wrap literal text as a layout document.', '返回该模板参数的完整源码文本。\n        Return the complete source text of this template parameter.')
        path.write_text(text, encoding='utf-8')

    path = ROOT / 'src/xr_syntax/core/document.py'
    text = path.read_text(encoding='utf-8')
    text = re.sub(
        r'(?m)^\s*# 高层编辑刻意返回重新解析后的新快照.*\n(?:\s*# .*\n){1,5}',
        '    # 高层编辑后重新解析，刷新 field 和 diagnostics；底层 tree 仍可复用 green 子树。\n'
        '    # High-level edits reparse to refresh fields and diagnostics; low-level edits still reuse green subtrees.\n',
        text,
    )
    path.write_text(text, encoding='utf-8')

    path = ROOT / 'src/xr_syntax/core/red.py'
    text = path.read_text(encoding='utf-8')
    text = re.sub(
        r'(?m)^\s*# path 只在当前快照内有意义.*\n(?:\s*# .*\n){1,4}',
        '        # path 记录当前 snapshot 内的结构 child 索引。\n'
        '        # The path records structural child indices in the current snapshot.\n',
        text,
    )
    text = re.sub(
        r'(?m)^\s*# 绝对位置在这里根据不可变 child.*\n(?:\s*# .*\n){1,4}',
        '        # 绝对位置由前序 child 的字节宽度推导。\n'
        '        # Absolute positions are derived from preceding child byte widths.\n',
        text,
    )
    path.write_text(text, encoding='utf-8')

    path = ROOT / 'src/xr_syntax/cpp/document.py'
    text = path.read_text(encoding='utf-8')
    text = re.sub(
        r'(?m)^\s*# 区域配对只是建立在普通 C\+\+ 注释.*\n(?:\s*# .*\n){1,4}',
        '    # 区域标记由普通 C++ 注释配对得到，实现在 document 层。\n'
        '    # Region markers are paired from ordinary C++ comments at the document layer.\n',
        text,
    )
    path.write_text(text, encoding='utf-8')


def main():
    rename_package()
    replace_names()
    py38_compat()
    clean_docs_and_comments()
    targeted_cleanup()


if __name__ == '__main__':
    main()
