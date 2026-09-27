"""补充核验：反不正当竞争法（现行版）商业贿赂与损害赔偿的条号定位。

用法：runtime/Scripts/python.exe tests/_verify_expert_prompts2.py
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
    ("中华人民共和国反不正当竞争法", "第八条"),
    ("中华人民共和国反不正当竞争法", "第二十一条"),
    ("中华人民共和国反不正当竞争法", "第二十二条"),
    ("中华人民共和国反不正当竞争法", "第二十三条"),
]

out = {}
for law, art in TARGETS:
    try:
        raw = registry.dispatch("mcp__yuandian_law__yuandian_get_legal_article_detail",
                                {"regulation_name": law, "article_number": art})
        payload = json.loads(raw) if isinstance(raw, str) else {}
        t = payload.get("result", "")
        try:
            parsed = json.loads(t) if isinstance(t, str) and t.strip().startswith(("{", "[")) else None
        except ValueError:
            parsed = None
        data = parsed.get("data") if isinstance(parsed, dict) else None
        body = ""
        if isinstance(data, dict):
            for key in ("content", "正文", "ftnr", "text", "llm_content"):
                v = data.get(key)
                if isinstance(v, str) and len(v) > 10:
                    body = v
                    break
    except Exception as e:
        body = f"<ERROR {type(e).__name__}: {e}>"
    out[f"{law}|{art}"] = body
    head = body[:150].replace("\n", " ") if body else "<空>"
    print(f"--- {law} {art}: {len(body)} 字 | {head}")

Path(BE / "tests" / "_verified_expert_prompts2.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
