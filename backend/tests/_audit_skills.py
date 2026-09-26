"""技能库审计：工具名引用解析 / 伴生文件缺失 / 绝对路径泄漏。

用法：runtime/Scripts/python.exe tests/_audit_skills.py
"""
import json
import re
from pathlib import Path

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"
inv = json.loads((BE / "tests" / "_tool_inventory.json").read_text(encoding="utf-8"))
all_names = inv["mcp"] + inv["builtin"]

TOK = re.compile(r"\b(yuandian_[a-z_]{3,}|mcp__[a-z_]{3,})\b")
BUILTIN_HINT = re.compile(
    r"\b(read_file|write_file|search_files|terminal|list_files|patch_file|apply_patch|"
    r"todo_write|web_search|web_fetch|skill_view)\b"
)

# 绝对路径/家目录泄漏（用 chr(92) 拼反斜杠，避开 heredoc 折叠）
BS = chr(92)
LEAK = re.compile(
    r"(?:~/|/home/|/Users/)[^\s\"'`)]{0,60}"
    r"|C:" + BS + BS + r"Users" + BS + BS + r"[^\s\"'`)]{0,60}"
    r"|D:" + BS + BS + r"Down" + BS + BS + r"[^\s\"'`)]{0,60}"
)

unresolved, refs_missing, abs_leak = {}, {}, {}
resolved_cnt = 0
total = 0

for sm in sorted(SK.rglob("SKILL.md")):
    sid = str(sm.relative_to(SK).parent).replace(BS, "/")
    txt = sm.read_text(encoding="utf-8", errors="replace")
    total += 1
    toks = set(TOK.findall(txt)) | set(BUILTIN_HINT.findall(txt))
    bad = set()
    for t in toks:
        if any(t in n for n in all_names):
            resolved_cnt += 1
        else:
            bad.add(t)
    if bad:
        unresolved[sid] = bad
    miss = set()
    for m in re.finditer(
        r"(?:references|profiles|connectors|workflows|assets)/[A-Za-z0-9_\u4e00-\u9fff.\-]+\.(?:md|json|yaml|yml|txt)",
        txt,
    ):
        if not (sm.parent / m.group(0)).exists():
            miss.add(m.group(0))
    if miss:
        refs_missing[sid] = miss
    leaks = set(LEAK.findall(txt))
    if leaks:
        abs_leak[sid] = leaks

print(f"技能总数: {total}")
print(f"工具引用解析命中次数: {resolved_cnt}")
print()
print(f"=== 引用了不存在工具的技能: {len(unresolved)} ===")
for sid, bad in sorted(unresolved.items()):
    print(f"  {sid}: {', '.join(sorted(bad))}")
print()
print(f"=== 引用了缺失伴生文件的技能: {len(refs_missing)} ===")
for sid, miss in sorted(refs_missing.items()):
    print(f"  {sid}: {', '.join(sorted(miss))[:130]}")
print()
print(f"=== 含绝对路径/家目录引用的技能: {len(abs_leak)} ===")
for sid, lk in sorted(abs_leak.items()):
    print(f"  {sid}: {', '.join(sorted(lk))[:110]}")
