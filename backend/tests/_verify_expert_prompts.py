"""专家体系 systemPrompt 法条核验：逐条取回现行条文原文（元典 MCP）。

用法：runtime/Scripts/python.exe tests/_verify_expert_prompts.py
输出：结果写入 tests/_verified_expert_prompts.json，并打印每条前 120 字供人工比对。
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
    # 民事诉讼法（现行版）：确认起诉状记载事项 / 举证责任 的现行条号
    ("中华人民共和国民事诉讼法", "第六十七条"),
    ("中华人民共和国民事诉讼法", "第一百二十二条"),
    ("中华人民共和国民事诉讼法", "第一百二十三条"),
    ("中华人民共和国民事诉讼法", "第一百二十四条"),
    # 公司法（2023 修订）：决议效力三兄弟
    ("中华人民共和国公司法", "第二十五条"),
    ("中华人民共和国公司法", "第二十六条"),
    ("中华人民共和国公司法", "第二十七条"),
    # 建设工程解释（一）：工期顺延现行条号（候选第17条），另探第10条排除混淆
    ("最高人民法院关于审理建设工程施工合同纠纷案件适用法律问题的解释（一）", "第十条"),
    ("最高人民法院关于审理建设工程施工合同纠纷案件适用法律问题的解释（一）", "第十七条"),
    # 反不正当竞争法（2025 修订后现行版）：商业贿赂与赔偿的现行条号
    ("中华人民共和国反不正当竞争法", "第七条"),
    ("中华人民共和国反不正当竞争法", "第九条"),
    ("中华人民共和国反不正当竞争法", "第十七条"),
    ("中华人民共和国反不正当竞争法", "第二十条"),
    # 专利法（2020 修正后现行版）：赔偿计算现行条号（候选第71条），另探第65条
    ("中华人民共和国专利法", "第六十五条"),
    ("中华人民共和国专利法", "第七十一条"),
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
        refs = {k: (str(v)[:80]) for k, v in data.items()
                if k not in ("content", "正文", "ftnr", "text", "llm_content")}
    out[f"{law}|{art}"] = {"text": body, "meta": refs}
    head = body[:120].replace("\n", " ") if body else f"<空 {r if isinstance(r, str) else ''}>"
    print(f"--- {law} {art}: {len(body)} 字 | {head}")

Path(BE / "tests" / "_verified_expert_prompts.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("已写入 tests/_verified_expert_prompts.json")
