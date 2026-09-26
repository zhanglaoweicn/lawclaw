"""卫星技能本地化收尾：标题去斜杠命令 + 修正《律师法》条号（2026 修正版已整体后移）。

发现：2026 修正版《律师法》中，保密义务是**第41条**（旧版第38条），
旧号第38条现为"调查取证权"。卫星技能沿用旧号会引错。

用法：runtime/Scripts/python.exe tests/_fix_investigation_satellites.py [--dry]
"""
import re
import sys
from pathlib import Path

SK = Path(r"D:\LawClaw\backend\.hermes\skills")
DRY = "--dry" in sys.argv
BS = chr(92)

TITLES = {
    "employment-investigation-open": "# 内部调查立案与方案",
    "employment-investigation-add": "# 内部调查材料归档",
    "employment-investigation-query": "# 内部调查问询与检索",
    "employment-investigation-memo": "# 内部调查报告（备忘录）",
    "employment-investigation-summary": "# 内部调查汇报摘要",
}

count = 0
for sid, title in TITLES.items():
    p = SK / sid / "SKILL.md"
    t = p.read_text(encoding="utf-8", errors="replace")
    o = t
    t = re.sub(r"(?m)^#\s*/investigation-[a-z]+\s*$", title, t)
    t = re.sub(r"(?m)^#\s*「?/investigation-[a-z]+」?\s*$", title, t)
    t = t.replace("《律师法》第38条保密义务", "《律师法》第41条保密义务")
    t = t.replace("《律师法》第38条", "《律师法》第41条")
    t = re.sub(r"律师法\s*第\s*38\s*条", "律师法第41条", t)
    if t != o:
        count += 1
        print(("【dry】" if DRY else "") + str(p.relative_to(SK)).replace(BS, "/"))
        if not DRY:
            p.write_text(t, encoding="utf-8", newline="\n")
print(f"改动文件数: {count}")
