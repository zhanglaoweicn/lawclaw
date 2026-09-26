"""已启用技能的缺陷交叉统计。

用法：runtime/Scripts/python.exe tests/_audit_enabled.py
"""
import re
from pathlib import Path

import yaml

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"

enabled = (yaml.safe_load((BE / ".hermes" / "config.yaml").read_text(encoding="utf-8"))
           .get("skills") or {}).get("enabled") or []

US_MARKERS = [
    "EEOC", "DFEH", "at-will", "at will", "state law", "USD", "FLSA",
    "Title VII", "OSHA", "W-2", "1099", "paralegal", "Delaware",
    "GDPR", "CCPA", "HIPAA", "discovery", "deposition",
]
GATE = "STOP before doing substantive work"

rows = []
for e in enabled:
    d = SK / e
    sm = d / "SKILL.md"
    if not sm.exists():
        rows.append((e, "缺少 SKILL.md"))
        continue
    txt = sm.read_text(encoding="utf-8", errors="replace")
    defects = []
    if "CLAUDE_PLUGIN_ROOT" in txt:
        defects.append("未展开变量 ${CLAUDE_PLUGIN_ROOT}")
    cl = d / "CLAUDE.md"
    gated = False
    if cl.exists():
        ct = cl.read_text(encoding="utf-8", errors="replace")
        if GATE in ct and "~/.claude/plugins/config" in ct:
            gated = True
            defects.append("门禁指向 ~/.claude 配置（缺失即停止工作）")
    if "yuandian_rh_" in txt or "yuandian_case_vector_search" in txt or "yuandian_law_vector_search" in txt:
        defects.append("引用旧元典工具名")
    if re.search(r"(?<!~/ )CLAUDE\.md", txt.replace("~/CLAUDE.md", "")) and not cl.exists() and not gated:
        defects.append("要求读 CLAUDE.md 但文件缺失")
    us = sorted({m.strip() for m in US_MARKERS if m in txt})
    if us:
        defects.append("美国法残留: " + ",".join(us[:4]))
    if defects:
        rows.append((e, "; ".join(defects)))

print(f"启用技能总数: {len(enabled)}")
print(f"存在缺陷的启用技能: {len(rows)}")
print()
for name, d in rows:
    print(f"  {name}")
    print(f"      {d}")
print()

from collections import Counter  # noqa: E402

c = Counter()
for _n, d in rows:
    for part in d.split("; "):
        c[part.split(":")[0]] += 1
print("缺陷类型计数:")
for k, v in c.most_common():
    print(f"  {v:3d}  {k}")
