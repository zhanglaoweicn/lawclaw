"""第二批法条核验（新技能将引用的关键条文）。

用法：runtime/Scripts/python.exe tests/_verify_articles2.py
"""
import json
import os
import sys
from pathlib import Path

PROJ = Path(r"D:\LawClaw")
BE = PROJ / "backend"
sys.path.insert(0, str(PROJ))
sys.path.insert(0, str(BE))
for line in (BE / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())
os.environ.setdefault("HERMES_HOME", str(BE / ".hermes"))

from tools.mcp_tool_discovery import discover_mcp_tools  # noqa: E402
from tools.registry import registry  # noqa: E402

discover_mcp_tools()

TARGETS = [
    ("中华人民共和国民法典", "658"),
    ("中华人民共和国民法典", "1062"),
    ("中华人民共和国民法典", "1063"),
    ("中华人民共和国民法典", "1091"),
    ("中华人民共和国民法典", "1092"),
    ("中华人民共和国民法典", "367"),
    ("最高人民法院关于审理民间借贷案件适用法律若干问题的规定", "25"),
    ("最高人民法院关于审理民间借贷案件适用法律若干问题的规定", "16"),
    ("最高人民法院关于审理民间借贷案件适用法律若干问题的规定", "26"),
    ("中华人民共和国民法典", "563"),
    ("中华人民共和国民法典", "577"),
    ("中华人民共和国民法典", "610"),
    ("中华人民共和国民法典", "716"),
    ("中华人民共和国民法典", "721"),
    ("中华人民共和国民法典", "722"),
    ("工伤保险条例", "21"),
    ("工伤保险条例", "37"),
    ("中华人民共和国刑事诉讼法", "67"),
    ("中华人民共和国律师法", "33"),
]


def call(args):
    raw = registry.dispatch("mcp__yuandian_law__yuandian_get_legal_article_detail", args)
    if not isinstance(raw, str):
        return None
    try:
        p = json.loads(raw)
    except ValueError:
        return None
    if isinstance(p, dict) and p.get("error"):
        return {"__err": str(p["error"])[:120]}
    t = p.get("result", "")
    try:
        return json.loads(t) if isinstance(t, str) and t.strip().startswith("{") else None
    except ValueError:
        return None


out = {}
for law, art in TARGETS:
    p = call({"regulation_name": law, "article_number": art})
    data = (p or {}).get("data") if isinstance(p, dict) else None
    txt, meta = "", {}
    if isinstance(data, dict):
        for key in ("content", "正文", "ftnr", "text", "llm_content"):
            if isinstance(data.get(key), str) and len(data[key]) > 10:
                txt = data[key]
                break
        meta = {k: v for k, v in data.items() if k in ("title", "sxx", "sxrq", "gbrq", "type")}
    out[f"{law}|{art}"] = {"text": txt, "meta": meta}
    print(f"{'命中' if txt else '未命中'} {law} {art} {meta.get('title','')} | {txt[:110].replace(chr(10),' ')}")

Path(BE / "tests" / "_verified_articles2.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("已写入 tests/_verified_articles2.json")
