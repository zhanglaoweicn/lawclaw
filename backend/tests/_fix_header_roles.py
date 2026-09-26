"""工作成果标头改为按角色三档（外部律师 / 企业法务 / 非律师）。

背景：2026-09-27 产品决策——企业内部法务同样是目标客户，标头不能只按"律师"一刀切
（此前误把"仅供法务团队使用"从律师档删掉，导致企业法务场景缺档位）。

用法：runtime/Scripts/python.exe tests/_fix_header_roles.py [--dry]
"""
import sys
from pathlib import Path

SK = Path(r"D:\LawClaw\backend\.hermes\skills")
DRY = "--dry" in sys.argv

OLD = "- 律师 + 中国法：`保密 / 内部法律分析 — 不构成外发法律意见`"
NEW = ("- 外部执业律师：`保密 / 内部法律分析（律师工作成果） — 不构成外发法律意见`\n"
       "- 企业法务（内部）：`保密 / 法务工作成果 — 仅供内部使用 — 不构成外发法律意见`")

count = 0
for p in sorted(SK.rglob("*.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    if OLD not in t:
        continue
    t = t.replace(OLD, NEW)
    count += 1
    print("更新: " + str(p.relative_to(SK)).replace(chr(92), "/"))
    if not DRY:
        p.write_text(t, encoding="utf-8", newline="\n")
print(f"{'【dry-run】' if DRY else ''}更新文件数: {count}")
