"""全库工具名解析检查（覆盖蛇形与驼峰两类旧名）。

用法：runtime/Scripts/python.exe tests/_audit_toolrefs.py
"""
import json
import re
from pathlib import Path

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"
inv = json.loads((BE / "tests" / "_tool_inventory.json").read_text(encoding="utf-8"))
all_names = inv["mcp"] + inv["builtin"]
BS = chr(92)

# 任何形如 yuandian_xxx / mcp__xxx 的引用（大小写都抓）
TOK = re.compile(r"\b(yuandian_[A-Za-z_]{2,}|mcp__[A-Za-z_]{3,})\b")

bad_by_skill = {}
for sm in sorted(SK.rglob("SKILL.md")):
    sid = str(sm.relative_to(SK).parent).replace(BS, "/")
    txt = sm.read_text(encoding="utf-8", errors="replace")
    bad = set()
    for t in set(TOK.findall(txt)):
        if not any(n.endswith(t) or t in n for n in all_names):
            bad.add(t)
    if bad:
        bad_by_skill[sid] = bad

print(f"引用了无法解析的工具名的技能: {len(bad_by_skill)}")
print(f"无法解析的工具引用总数: {sum(len(v) for v in bad_by_skill.values())}")
print()
for sid, bad in sorted(bad_by_skill.items(), key=lambda kv: -len(kv[1])):
    print(f"  {sid}  ({len(bad)} 个)")
    for t in sorted(bad):
        print(f"      {t}")
