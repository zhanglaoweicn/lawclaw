"""未本地化技能加警示横幅 + 修正缺失伴生文件引用。

1) 给两个 100% 英文（美国法实务）的技能加显著横幅，避免误用
2) element-templates-cn.md → 实际存在的 element-templates.md
3) company-profile-template.md → 按 LawClaw 约定指向共享画像路径

用法：runtime/Scripts/python.exe tests/_fix_misc.py
"""
from pathlib import Path

SK = Path(r"D:\LawClaw\backend\.hermes\skills")

BANNER = """> ⚠️ **本技能尚未本地化，LawClaw 默认不启用。**
> 正文为美国法实务（联邦/州劳动法程序、EEOC/DFEH、NLRA 等），在中国法下直接使用会给出错误结论。
> 若需要「内部调查」能力，应基于《劳动合同法》《劳动法》与用人单位规章制度重新编写，
> 而不是启用本文件。以下原文保留仅作结构参考。

"""

for sid in ("employment-internal-investigation", "employment-international-expansion"):
    p = SK / sid / "SKILL.md"
    t = p.read_text(encoding="utf-8", errors="replace")
    if "本技能尚未本地化" in t:
        print(f"{sid}: 已有横幅，跳过")
        continue
    if not t.startswith("---"):
        print(f"{sid}: 非 frontmatter 开头，跳过")
        continue
    end = t.find("---", 3)
    head, body = t[: end + 3], t[end + 3:]
    p.write_text(head + "\n\n" + BANNER + body.lstrip("\n"), encoding="utf-8", newline="\n")
    print(f"{sid}: 已加横幅")

count = 0
for p in sorted(SK.rglob("*.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    o = t
    t = t.replace("references/element-templates-cn.md", "references/element-templates.md")
    t = t.replace(
        "`references/company-profile-template.md` 中的模板",
        "`$LEGAL_AGENT_PROFILE_HOME/company-profile.md`（不存在时按下面的问题清单直接创建）",
    )
    t = t.replace(
        "`references/company-profile-template.md` 的模板",
        "`$LEGAL_AGENT_PROFILE_HOME/company-profile.md`（不存在时按下面的问题清单直接创建）",
    )
    if t != o:
        p.write_text(t, encoding="utf-8", newline="\n")
        count += 1
        print("修正引用: " + str(p.relative_to(SK)).replace(chr(92), "/"))
print(f"引用修正文件数: {count}")
