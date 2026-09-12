# -*- coding: utf-8 -*-
"""claude-for-legal-ZH 增量领域插件安装脚本（Apache 2.0，源：zhou210712/claude-for-legal-ZH）。

- 6 个律师业务领域插件：employment / ip / ai-governance / privacy / regulatory / product
- 目录与 frontmatter name 统一前缀化（employment-termination-review），防跨插件同名冲突
- SKILL.md 内部 `~/.claude/plugins/config/claude-for-legal/<plugin>/` 路径改写为技能目录绝对路径
  （agent 的 read_file 可直达）；插件根 CLAUDE.md 与 references/ 随附到每个技能目录
- 跳过各插件 customize / matter-workspace（与 LawClaw 原生技能体系/案件管理重叠）
- 幂等：重复运行覆盖更新

用法：python scripts/install_cfl_skills.py [--source D:/Down/claude-for-legal-ZH]
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
SKILLS_DIR = BACKEND / ".hermes" / "skills"

PLUGINS = {
    "employment-legal": "employment",
    "ip-legal": "ip",
    "ai-governance-legal": "ai-governance",
    "privacy-legal": "privacy",
    "regulatory-legal": "regulatory",
    "product-legal": "product",
}
SKIP_SKILLS = {"customize", "matter-workspace"}


def install(source: Path) -> dict:
    installed: dict[str, str] = {}
    for plugin, prefix in PLUGINS.items():
        src_skills = source / plugin / "skills"
        if not src_skills.is_dir():
            print(f"[SKIP] {plugin}: skills 目录不存在")
            continue
        plugin_claude_md = source / plugin / "CLAUDE.md"
        plugin_refs = source / plugin / "references"
        for skill_dir in sorted(src_skills.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name in SKIP_SKILLS:
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            target_name = f"{prefix}-{skill_dir.name}"
            target = SKILLS_DIR / target_name
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)
            # SKILL.md：name 前缀化 + 路径改写
            text = skill_md.read_text(encoding="utf-8")
            text = re.sub(r"^(name:\s*)", rf"\g<1>{prefix}-", text, count=1, flags=re.M)
            text = text.replace(
                f"~/.claude/plugins/config/claude-for-legal/{plugin}/",
                f"{(SKILLS_DIR / target_name).as_posix()}/",
            )
            # 兜底：仍残留的 claude-for-legal 绝对引用（如 ~/.claude/plugins/... 其他写法）
            text = re.sub(
                r"~/\.claude/plugins/config/claude-for-legal/[a-z0-9-]+/",
                f"{(SKILLS_DIR / target_name).as_posix()}/",
                text,
            )
            (target / "SKILL.md").write_text(text, encoding="utf-8")
            # 插件级资产随附（CLAUDE.md 画像 + references 领域规则）
            if plugin_claude_md.exists():
                shutil.copy2(plugin_claude_md, target / "CLAUDE.md")
            if plugin_refs.is_dir():
                shutil.copytree(plugin_refs, target / "references", dirs_exist_ok=True)
            installed[target_name] = plugin
            print(f"[OK] {target_name}  ({plugin})")
    return installed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(Path(os.environ.get("CFL_ZH_SOURCE", "D:/Down/claude-for-legal-ZH"))))
    args = ap.parse_args()
    src = Path(args.source)
    if not src.is_dir():
        print(f"源不存在：{src}——请先 git clone --depth 1 https://github.com/zhou210712/claude-for-legal-ZH")
        sys.exit(2)
    res = install(src)
    print(f"\n共安装 {len(res)} 个技能")
    (REPO_ROOT / "scripts" / "cfl_installed.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
