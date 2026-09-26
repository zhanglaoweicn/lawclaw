"""对未命中的条文用变体重试（条号格式 / 法规全称差异）。

用法：runtime/Scripts/python.exe tests/_verify_retry.py
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

CASES = [
    ("中华人民共和国民法典", ["726", "第七百二十六条", "725"]),
    ("中华人民共和国民法典", ["728", "第七百二十八条"]),
    ("工伤保险条例", ["14", "第十四条"]),
    ("工伤保险条例", ["17", "第十七条"]),
    ("工伤保险条例", ["33", "第三十三条"]),
    ("中华人民共和国工伤保险条例", ["14"]),
    ("中华人民共和国刑事诉讼法", ["39", "第三十九条"]),
    ("中华人民共和国刑事诉讼法", ["38", "第三十八条"]),
    ("中华人民共和国刑事诉讼法", ["95", "第九十五条"]),
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
        return {"error": str(p["error"])[:120]}
    t = p.get("result", "")
    try:
        return json.loads(t) if isinstance(t, str) and t.strip().startswith("{") else None
    except ValueError:
        return None


for law, nums in CASES:
    for n in nums:
        p = call({"regulation_name": law, "article_number": n})
        data = (p or {}).get("data") if isinstance(p, dict) else None
        txt = ""
        if isinstance(data, dict):
            for key in ("content", "正文", "ftnr", "text", "llm_content"):
                if isinstance(data.get(key), str) and len(data[key]) > 10:
                    txt = data[key]
                    break
        mark = "命中 " + str(len(txt)) + " 字 | " + txt[:120].replace(chr(10), " ") if txt else "未命中"
        print(f"{law} | {n}: {mark}")
