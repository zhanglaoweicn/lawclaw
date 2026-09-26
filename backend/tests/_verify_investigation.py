"""内部调查技能的法条核验（中国法）。

用法：runtime/Scripts/python.exe tests/_verify_investigation.py
输出：tests/_verified_investigation.json
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
    ("中华人民共和国劳动合同法", "4"),
    ("中华人民共和国劳动合同法", "36"),
    ("中华人民共和国劳动合同法", "39"),
    ("中华人民共和国劳动合同法", "40"),
    ("中华人民共和国劳动合同法", "43"),
    ("中华人民共和国劳动合同法", "46"),
    ("中华人民共和国劳动合同法", "47"),
    ("中华人民共和国劳动合同法", "48"),
    ("中华人民共和国劳动合同法", "50"),
    ("中华人民共和国劳动合同法", "87"),
    ("中华人民共和国劳动争议调解仲裁法", "6"),
    ("中华人民共和国劳动争议调解仲裁法", "27"),
    ("中华人民共和国个人信息保护法", "13"),
    ("中华人民共和国个人信息保护法", "17"),
    ("中华人民共和国民法典", "1032"),
    ("中华人民共和国民法典", "1033"),
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


out = {}
miss = []
for law, art in TARGETS:
    p = call({"regulation_name": law, "article_number": art})
    data = (p or {}).get("data") if isinstance(p, dict) else None
    txt, meta = "", {}
    if isinstance(data, dict):
        for key in ("content", "正文", "ftnr", "text", "llm_content"):
            if isinstance(data.get(key), str) and len(data[key]) > 10:
                txt = data[key]
                break
        meta = {k: v for k, v in data.items() if k in ("title", "sxx", "sxrq")}
    if not txt:
        miss.append(f"{law}|{art}")
    out[f"{law}|{art}"] = {"text": txt, "meta": meta}
    print(f"{'命中' if txt else '未命中'} {law} {art} | {meta.get('title','')} | {txt[:90].replace(chr(10),' ')}")

Path(BE / "tests" / "_verified_investigation.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(f"\n未命中 {len(miss)}: {miss}")
