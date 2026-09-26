"""全库修正陈旧的《律师法》条号：第38条(保密义务) → 第41条（2026 修正版）。

背景：2026 修正版《律师法》条文序号整体后移——保密义务由旧第38条变为第41条；
现第38条是"调查取证权"。技能库里 67 处引用沿用旧号（引文内容本身与第41条原文一致，
只有条号陈旧）。**跳过明确标注"（调查取证）"的那处**（那是正确的新号用法）。

用法：runtime/Scripts/python.exe tests/_fix_lawyer_law_number.py [--dry]
"""
import re
import sys
from pathlib import Path

SK = Path(r"D:\LawClaw\backend\.hermes\skills")
DRY = "--dry" in sys.argv
BS = chr(92)

pat = re.compile(r"(《?律师法》?)\s*第\s*38\s*条")

count = 0
files = []
for p in sorted(SK.rglob("*.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    out, n, pos = [], 0, 0
    for m in pat.finditer(t):
        tail = t[m.end(): m.end() + 12]
        if "调查取证" in tail:
            continue
        out.append(t[pos:m.start()])
        out.append(f"{m.group(1)}第41条")
        pos = m.end()
        n += 1
    if n:
        out.append(t[pos:])
        files.append(str(p.relative_to(SK)).replace(BS, "/"))
        count += n
        if not DRY:
            p.write_text("".join(out), encoding="utf-8", newline="\n")

print(("【dry-run】" if DRY else "") + f"修正 {count} 处，涉及 {len(files)} 个文件")
for f in files[:8]:
    print("   " + f)
