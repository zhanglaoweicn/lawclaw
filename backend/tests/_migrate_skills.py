"""技能库迁移：把 Claude Code 时代的配置路径/门禁/命令统一到 LawClaw 约定。

依据 `legal/legal-profile-interview-ops/SKILL.md` 定义的权威约定：
  - 画像 = `$LEGAL_AGENT_PROFILE_HOME/<bundle_id>/profile.md`
  - 共享公司画像 = `$LEGAL_AGENT_PROFILE_HOME/company-profile.md`
  - 其它状态文件（leave-register.yaml / verification-log.md / portfolio.yaml / ai-systems.yaml）
    同置于 `<bundle_id>/` 目录下

幂等：重复执行不会再改动（规则命中即替换为不含旧式的文本）。
用法：runtime/Scripts/python.exe tests/_migrate_skills.py [--dry]
"""
import re
import sys
from pathlib import Path

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"
DRY = "--dry" in sys.argv

BUNDLES = {
    "litigation-": "litigation-legal",
    "commercial-": "commercial-legal",
    "corporate-": "corporate-legal",
    "prc-legal-research-": "legal-research-cn",
    "employment-": "employment-legal",
    "ip-": "ip-legal",
    "privacy-": "privacy-legal",
    "product-": "product-legal",
    "regulatory-": "regulatory-legal",
    "ai-governance-": "ai-governance-legal",
}
CFL_CARDS = {
    "employment-legal": "劳动法插件初始化访谈",
    "ip-legal": "知识产权插件初始化访谈",
    "privacy-legal": "隐私合规初始化访谈",
    "product-legal": "产品合规初始化访谈",
    "regulatory-legal": "监管合规初始化访谈",
    "ai-governance-legal": "AI治理插件初始化访谈",
}
CARD_MAP = {
    "/ip-legal:portfolio": "「知识产权组合盘点」",
    "/employment-legal:log-leave": "「员工假期登记」",
    "/ai-governance-legal:ai-inventory": "「AI使用清单盘点」",
    "/product-legal:matter-workspace": "「产品合规事项工作区」",
    "/employment-legal:termination-review": "「解除劳动合同审查」",
    "/termination-review": "「解除劳动合同审查」",
}

CONFIG_BLOCK = """<!--
配置与画像位置（LawClaw 桌面版）

本插件的实务画像（律师个人／团队的执业设定、审查阈值、风险口径、输出格式）保存在：

  $LEGAL_AGENT_PROFILE_HOME/{bundle}/profile.md

规则：
1. 从该路径读取配置；不要从本文件读取用户数据。
2. 若该文件不存在或仍含 [PLACEHOLDER]：**照常工作，不要拒绝、不要要求用户先去配置**。
   按中国法与通用最佳实践给出完整输出，并在结尾用一句话提示律师：
   跑「{card}」技能卡（技能页搜索即可）可让本技能的输出贴合其执业口径。
3. 冷启动访谈与各项设置写入该路径，必要时创建父目录。
4. 本文件是**模板**，随技能分发、展示配置应有的结构；请勿把用户数据写在这里。
5. 跨插件共享的公司画像在 `$LEGAL_AGENT_PROFILE_HOME/company-profile.md`
   （位于 {bundle} 目录的上层），读取本插件画像前先读它；不存在时由冷启动访谈创建。
-->"""


def bundle_of(sid: str):
    for pref, b in BUNDLES.items():
        if sid.startswith(pref):
            return b
    return None


def migrate(text: str, bundle):
    n = {}
    t, c = re.subn(
        r"~/\.claude/plugins/config/claude-for-legal/([a-z-]+)/CLAUDE\.md",
        lambda m: f"$LEGAL_AGENT_PROFILE_HOME/{m.group(1)}/profile.md",
        text,
    )
    n["配置CLAUDE转profile"] = c
    text = t
    t, c = re.subn(r"~/\.claude/plugins/config/claude-for-legal/", "$LEGAL_AGENT_PROFILE_HOME/", text)
    n["配置前缀"] = c
    text = t
    t, c = re.subn(r"~/\.claude/plugins/cache/claude-for-legal/[a-z-]+/<version>/CLAUDE\.md", "本插件的旧版配置", text)
    n["旧缓存路径"] = c
    text = t
    if bundle:
        new_block = CONFIG_BLOCK.format(bundle=bundle, card=CFL_CARDS.get(bundle, "对应领域插件初始化访谈"))
        t, c = re.subn(r"<!--\s*CONFIGURATION LOCATION.*?-->", lambda m: new_block, text, flags=re.S)
        n["门禁块"] = c
        text = t
    for cmd, card in CARD_MAP.items():
        if cmd in text:
            text = text.replace(cmd, card)
            n["技能卡:" + cmd] = 1
    if bundle and bundle in CFL_CARDS:
        t, c = re.subn(r"/" + re.escape(bundle) + r":cold-start-interview", "「" + CFL_CARDS[bundle] + "」", text)
        if c:
            n["技能卡:冷启动访谈"] = c
        text = t
    t, c = re.subn(r"\$\{CLAUDE_PLUGIN_ROOT\}/CLAUDE\.md", "本技能目录内的 CLAUDE.md（实务画像模板）", text)
    n["未展开变量(带文件)"] = c
    text = t
    t, c = re.subn(r"\$\{CLAUDE_PLUGIN_ROOT\}", "本技能目录", text)
    n["未展开变量"] = c
    text = t
    if bundle:
        t, c = re.subn(r"插件配置\s*`?CLAUDE\.md`?", f"实务画像 `$LEGAL_AGENT_PROFILE_HOME/{bundle}/profile.md`", text)
        n["旧CLAUDE引用"] = c
        text = t
    # 元力工场四族不随技能附带 CLAUDE.md：其正文里的裸 CLAUDE.md 一律指向画像文件
    # （cfl 六族不同——它们确实各带一份 CLAUDE.md 模板，正文引用 ./CLAUDE.md 有效）
    if bundle in ("litigation-legal", "commercial-legal", "corporate-legal", "legal-research-cn"):
        t, c = re.subn(r"`CLAUDE\.md`", f"实务画像 `$LEGAL_AGENT_PROFILE_HOME/{bundle}/profile.md`", text)
        n["裸CLAUDE引用"] = c
        text = t
        # 不带反引号的裸引用（"实务级 CLAUDE.md"/"以 CLAUDE.md `## 输出`"）；
        # 先保护 `~/CLAUDE.md`（那是"禁止读取个人文件"的语句，不能替换）
        text = text.replace("~/CLAUDE.md", "\x00HOME_CLAUDE\x00")
        t, c = re.subn(r"CLAUDE\.md", f"$LEGAL_AGENT_PROFILE_HOME/{bundle}/profile.md", text)
        if c:
            n["裸引用(无反引号)"] = c
        text = t.replace("\x00HOME_CLAUDE\x00", "~/CLAUDE.md")
    if bundle:
        # ./CLAUDE.md 与 ./xxx.yaml 都是 Claude Code 的插件根相对写法，LawClaw 无此语义
        t, c = re.subn(r"`?\./CLAUDE\.md`?",
                       f"`$LEGAL_AGENT_PROFILE_HOME/{bundle}/profile.md`", text)
        n["相对CLAUDE路径"] = c
        text = t
        t, c = re.subn(r"`\./([A-Za-z0-9_-]+\.ya?ml)`",
                       lambda m: f"`$LEGAL_AGENT_PROFILE_HOME/{bundle}/{m.group(1)}`", text)
        n["相对yaml路径"] = c
        text = t
    t, c = re.subn(r"保密 / 内部法律分析 — 仅供法务团队使用 — 不构成外发法律意见",
                   "保密 / 内部法律分析 — 不构成外发法律意见", text)
    n["标头"] = c
    text = t
    # 删除“从 Claude Code 旧缓存迁移配置”的整句/整项指令（LawClaw 无此缓存，属死指令）
    t, c = re.subn(r"[^。\n]*~/\.claude/plugins/cache[^。\n]*。", "", text)
    if c:
        n["旧缓存死指令"] = c
        text = t
    t, c = re.subn(r"(?m)^\s*\d+\.\s*\*{0,2}迁移[:：].*$\n?", "", text)
    if c:
        n["迁移项(编号)"] = c
        text = t
    t, c = re.subn(r"(?m)^如果旧缓存路径.*$\n?", "", text)
    if c:
        n["迁移项(整句)"] = c
        text = t
    t, c = re.subn(r"(?m)^\s*\d+\.\s*\*{0,2}(迁移|Migration)\*{0,2}[:：]?\s*$", "", text)
    if c:
        n["迁移项(空壳)"] = c
        text = t
    text = re.sub(r"(?m)^\s*\d+\.\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, n


total = {}
changed = []
for p in sorted(SK.rglob("*.md")):
    sid = str(p.relative_to(SK).parent).replace("\\", "/")
    b = bundle_of(sid)
    src = p.read_text(encoding="utf-8", errors="replace")
    out, stats = migrate(src, b)
    if out != src:
        changed.append(sid)
        if not DRY:
            p.write_text(out, encoding="utf-8", newline="\n")
        for k, v in stats.items():
            if v:
                total[k] = total.get(k, 0) + v

print(("【dry-run】" if DRY else "") + f"改动文件数: {len(changed)}")
print("规则命中统计:")
for k, v in sorted(total.items(), key=lambda kv: -kv[1]):
    print(f"  {v:4d}  {k}")
