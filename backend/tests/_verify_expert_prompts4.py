"""补充核验4：用元典法条关键词检索定位执行编现行条号。

用法：runtime/Scripts/python.exe tests/_verify_expert_prompts4.py
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

QUERIES = [
    "申请执行的期间为二年",
    "认为执行行为违反法律规定 提出书面异议",
    "案外人 对执行标的提出书面异议",
    "迟延履行期间的债务利息",
]

for q in QUERIES:
    try:
        raw = registry.dispatch("mcp__yuandian_law__yuandian_search_legal_articles",
                                {"keyword": q, "page_size": 5})
        payload = json.loads(raw) if isinstance(raw, str) else {}
        t = payload.get("result", "")
        try:
            parsed = json.loads(t) if isinstance(t, str) and t.strip().startswith(("{", "[")) else None
        except ValueError:
            parsed = None
        data = parsed.get("data") if isinstance(parsed, dict) else None
        rows = []
        if isinstance(data, dict):
            rows = data.get("lst") or data.get("list") or data.get("rows") or []
        print(f"=== {q}: {len(rows)} 条")
        for r in rows[:5]:
            if not isinstance(r, dict):
                continue
            name = r.get("fgmc") or r.get("title") or r.get("regulation_name") or "?"
            art = r.get("fbtz") or r.get("article_number") or r.get("clause") or "?"
            body = r.get("content") or r.get("llm_content") or ""
            print(f"  [{name}] {art} | {str(body)[:100]}")
    except Exception as e:
        print(f"=== {q}: ERROR {type(e).__name__}: {e}")
