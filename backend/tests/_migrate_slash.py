"""斜杠命令与家目录路径的彻底迁移（补齐上一轮漏掉的范围）。

上一轮只映射了冷启动访谈与 6 个具体命令，实际全库还有 45 种命令（约 150 处）。
本次按「/bundle:skill → 对应技能的中文显示名」成批映射；对指向未安装技能包或
纯占位符的命令，改为中文通用表述。同时把示例里的 macOS/Linux 风格家目录路径
改为平台中立的占位符。

用法：runtime/Scripts/python.exe tests/_migrate_slash.py [--dry]
"""
import re
import sys
from pathlib import Path

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"
DRY = "--dry" in sys.argv
BS = chr(92)

src = (BE / "main.py").read_text(encoding="utf-8")
body = re.search(r"SKILL_DISPLAY_NAMES = \{(.*?)\n\}", src, re.S).group(1)
DISPLAY = dict(re.findall(r'"([a-z0-9\-/]+)"\s*:\s*"([^"]+)"', body))
DIRS = {d.name for d in SK.iterdir() if d.is_dir()}

CMD = re.compile(r"/([a-z][a-z0-9-]*):([a-z0-9-]+)")

HOME_FIX = [
    (re.compile(r"~/Downloads/([^\s`）)，、]*)"), r"<本地路径>/\1"),
    (re.compile(r"~/Documents/([^\s`）)，、]*)"), r"<本地路径>/\1"),
    (re.compile(r"~/code/[^\s`）)，、]*"), "<项目目录>"),
]


def resolve(bundle: str, skill: str):
    domain = bundle[:-6] if bundle.endswith("-legal") else bundle
    for cand in (f"{domain}-{skill}", skill, f"{bundle}-{skill}"):
        if cand in DISPLAY:
            return DISPLAY[cand]
    return None


stats = {}
changed = []
for p in sorted(SK.rglob("*.md")):
    t = p.read_text(encoding="utf-8", errors="replace")
    o = t

    def sub_cmd(m):
        name = resolve(m.group(1), m.group(2))
        if name:
            stats["映射为技能卡"] = stats.get("映射为技能卡", 0) + 1
            return f"「{name}」技能卡"
        key = "通用化(" + m.group(1) + ")"
        stats[key] = stats.get(key, 0) + 1
        return "技能页中的相关技能卡"

    t = CMD.sub(sub_cmd, t)

    t2, c = re.subn(r'插件命令跳转（"接下来请运行\s*技能页中的相关技能卡……"）',
                    '技能跳转提示（"接下来请运行 XX 技能……"）', t)
    if c:
        stats["元规则改写"] = stats.get("元规则改写", 0) + c
    t = t2

    for rx, rep in HOME_FIX:
        t, c = rx.subn(rep, t)
        if c:
            stats["家目录路径"] = stats.get("家目录路径", 0) + c

    if t != o:
        changed.append(str(p.relative_to(SK)).replace(BS, "/"))
        if not DRY:
            p.write_text(t, encoding="utf-8", newline="\n")

print(("【dry-run】" if DRY else "") + f"改动文件数: {len(changed)}")
for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
    print(f"  {v:4d}  {k}")
print("样例:", changed[:5])
