"""补充核验：律师法保密义务条 + 工会法通知工会条（卫星技能与底座引用的条文）。

用法：runtime/Scripts/python.exe tests/_verify_more.py
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
    ("中华人民共和国律师法", "38"),
    ("中华人民共和国律师法", "37"),
    ("中华人民共和国工会法", "21"),
    ("中华人民共和国工会法", "22"),
    ("中华人民共和国劳动合同法", "42"),
    ("中华人民共和国劳动合同法", "38"),
    ("中华人民共和国劳动合同法", "41"),
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
        return {"__err": str(p["error"])[:150]}
    t = p.get("result", "")
    try:
        return json.loads(t) if isinstance(t, str) and t.strip().startswith("{") else None
    except ValueError:
        return None


for law, art in TARGETS:
    p = call({"regulation_name": law, "article_number": art})
    data = (p or {}).get("data") if isinstance(p, dict) else None
    txt, title = "", ""
    if isinstance(data, dict):
        title = str(data.get("title") or "")
        for key in ("content", "正文", "ftnr", "text", "llm_content"):
            if isinstance(data.get(key), str) and len(data[key]) > 10:
                txt = data[key]
                break
    print(f"{'命中' if txt else '未命中'} {law} {art} | {title}")
    if txt:
        print("   " + txt[:200].replace(chr(10), " "))
