"""法条核验：为待编写的技能逐条取回条文原文（元典 MCP）。

用法：runtime/Scripts/python.exe tests/_verify_articles.py
输出：结果写入 tests/_verified_articles.json，并打印摘要供人工核对。
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
    ("中华人民共和国民法典", "第一千零七十六条"),
    ("中华人民共和国民法典", "第一千零七十七条"),
    ("中华人民共和国民法典", "第一千零七十八条"),
    ("中华人民共和国民法典", "第一千零八十四条"),
    ("中华人民共和国民法典", "第一千零八十五条"),
    ("中华人民共和国民法典", "第一千零八十六条"),
    ("中华人民共和国民法典", "第一千零八十七条"),
    ("中华人民共和国民法典", "第一千零八十八条"),
    ("中华人民共和国民法典", "第一千零八十九条"),
    ("中华人民共和国民法典", "第一千零六十四条"),
    ("中华人民共和国民法典", "第三百六十六条"),
    ("中华人民共和国民法典", "第六百六十七条"),
    ("中华人民共和国民法典", "第六百七十六条"),
    ("中华人民共和国民法典", "第六百七十九条"),
    ("中华人民共和国民法典", "第六百八十条"),
    ("中华人民共和国民法典", "第一千二百零八条"),
    ("中华人民共和国民法典", "第一千二百一十三条"),
    ("中华人民共和国民法典", "第一千一百七十九条"),
    ("中华人民共和国道路交通安全法", "第七十六条"),
    ("中华人民共和国民法典", "第五百九十八条"),
    ("中华人民共和国民法典", "第七百零三条"),
    ("中华人民共和国民法典", "第七百二十六条"),
    ("中华人民共和国民法典", "第七百二十八条"),
    ("工伤保险条例", "第十四条"),
    ("工伤保险条例", "第十七条"),
    ("工伤保险条例", "第三十三条"),
    ("中华人民共和国刑事诉讼法", "第三十九条"),
    ("中华人民共和国刑事诉讼法", "第三十八条"),
    ("中华人民共和国刑事诉讼法", "第九十五条"),
]


def call(tool_short, args):
    name = f"mcp__yuandian_law__{tool_short}"
    try:
        raw = registry.dispatch(name, args)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    if not isinstance(raw, str):
        return {"error": str(raw)[:200]}
    try:
        payload = json.loads(raw)
    except ValueError:
        return {"error": raw[:200]}
    if isinstance(payload, dict) and payload.get("error"):
        return {"error": str(payload["error"])[:200]}
    return payload


def text_of(payload):
    t = payload.get("result", "")
    if payload.get("structuredContent") and not t:
        t = json.dumps(payload["structuredContent"], ensure_ascii=False)
    try:
        return json.loads(t) if isinstance(t, str) and t.strip().startswith(("{", "[")) else None
    except ValueError:
        return None


def extract_text(data):
    """从 data 里取出条文正文（字段名随元典版本变化，按优先级探测）。"""
    if not isinstance(data, dict):
        return ""
    for key in ("content", "正文", "ftnr", "text", "llm_content"):
        v = data.get(key)
        if isinstance(v, str) and len(v) > 10:
            return v
    for v in data.values():
        if isinstance(v, str) and len(v) > 30:
            return v
    return ""


out = {}
for law, art in TARGETS:
    r = call("yuandian_get_legal_article_detail",
             {"regulation_name": law, "article_number": art})
    parsed = text_of(r) if isinstance(r, dict) and "error" not in r else None
    data = parsed.get("data") if isinstance(parsed, dict) else None
    body = extract_text(data)
    refs = {}
    if isinstance(data, dict):
        refs = {k: v for k, v in data.items() if k not in ("content", "正文", "ftnr", "text", "llm_content")}
    out[f"{law}|{art}"] = {"text": body, "meta": refs}
    print(f"--- {law} {art}: {len(body)} 字")

Path(BE / "tests" / "_verified_articles.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("已写入 tests/_verified_articles.json")
