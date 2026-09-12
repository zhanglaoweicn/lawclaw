# -*- coding: utf-8 -*-
"""Release audit: integration test over WebSocket for LawClaw backend."""
import asyncio
import json
import os
import sys

import websockets

URI = "ws://127.0.0.1:9876"
_results = []


def record(name, ok, detail=""):
    _results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def rpc(ws, method, params=None, timeout=60):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"{method} timed out after {timeout}s")
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        # skip stream/legacy frames
        if msg.get("id") != 1:
            continue
        if "error" in msg:
            raise RuntimeError(f"{method} RPC error: {msg['error']}")
        return msg.get("result")


async def main():
    async with websockets.connect(URI, max_size=20 * 1024 * 1024) as ws:
        # 1. handshake
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
        record("handshake/ready", hello.get("event") == "ready",
               f"model={hello.get('model')} ag_ui={hello.get('ag_ui_version')}")

        # 2. initialize
        r = await rpc(ws, "initialize", {})
        record("initialize", bool(r), json.dumps(r, ensure_ascii=False)[:200])

        # 3. list_mcp_servers
        r = await rpc(ws, "list_mcp_servers", {})
        servers = r.get("servers", r) if isinstance(r, dict) else r
        n = len(servers) if isinstance(servers, list) else "?"
        record("list_mcp_servers", n == 6, f"{n} servers")

        # 4. list_hermes_skills（设计上只返回 config 启用的技能，当前为 26 个）
        r = await rpc(ws, "list_hermes_skills", {})
        skills = r.get("skills", r) if isinstance(r, dict) else r
        cnt = len(skills) if isinstance(skills, (list, dict)) else "?"
        record("list_hermes_skills", isinstance(cnt, int) and cnt >= 20, f"{cnt} skills (enabled-only)")

        # 5. legal_search (Yuandian HTTP API) — law
        r = await rpc(ws, "legal_search", {"query": "买卖合同 违约责任", "search_type": "law"}, timeout=45)
        results = r.get("results", []) if isinstance(r, dict) else []
        record("legal_search(law)", len(results) > 0,
               f"{len(results)} results, first={json.dumps(results[0], ensure_ascii=False)[:120] if results else 'N/A'}")

        # 6. legal_search — case
        r = await rpc(ws, "legal_search", {"query": "房屋租赁合同纠纷", "search_type": "case"}, timeout=45)
        results = r.get("results", []) if isinstance(r, dict) else []
        record("legal_search(case)", len(results) > 0, f"{len(results)} results")

        # 7. calc_limitation_period (诉讼时效)
        r = await rpc(ws, "calc_limitation_period", {"case_type": "contract", "event_date": "2024-01-15"})
        record("calc_limitation", isinstance(r, dict) and len(json.dumps(r)) > 10,
               json.dumps(r, ensure_ascii=False)[:160])

        # 8. calc_deadline
        r = await rpc(ws, "calc_deadline", {"start_date": "2026-09-11", "days": 15})
        record("calc_deadline", isinstance(r, dict), json.dumps(r, ensure_ascii=False)[:160])

        # 9. chat — full LLM round trip (short) with valid key override
        #    ⚠ 密钥不写死在测试里：优先读环境变量，缺省回落到后端 .env 的默认凭证
        AGNES_KEY = os.environ.get("LAWCLAW_TEST_API_KEY", "")
        AGNES_URL = os.environ.get("LAWCLAW_TEST_BASE_URL", "https://api.deepseek.com/v1")
        r = await rpc(ws, "chat", {
            "message": "用一句话回答：《民法典》诉讼时效一般为几年？",
            "api_key": AGNES_KEY or "demo-mode", "base_url": AGNES_URL, "model": os.environ.get("LAWCLAW_TEST_MODEL", "deepseek-flash"),
        }, timeout=180)
        text = ""
        if isinstance(r, dict):
            text = r.get("response") or r.get("text") or r.get("content") or json.dumps(r, ensure_ascii=False)
        record("chat(LLM+Agnes key)", bool(text) and len(text) > 5 and "未返回有效响应" not in text, text[:200])

        # 10. chat with default .env key (DeepSeek) — expected broken per audit
        r = await rpc(ws, "chat", {"message": "1+1=?只回答数字"}, timeout=120)
        text = (r or {}).get("response", "") if isinstance(r, dict) else ""
        record("chat(.env default key)", bool(text) and "未返回有效响应" not in text, text[:120])

        # 11. verify_citation
        r = await rpc(ws, "verify_citation", {"law": "民法典", "article": "第一百八十八条"}, timeout=45)
        record("verify_citation", isinstance(r, dict), json.dumps(r, ensure_ascii=False)[:150])

        # 12. recommend_skills_for_stage
        r = await rpc(ws, "recommend_skills_for_stage", {"stage": "诉讼中"})
        record("recommend_skills_for_stage", isinstance(r, dict), json.dumps(r, ensure_ascii=False)[:150])

    print("\n===== SUMMARY =====")
    fails = [x for x in _results if not x[1]]
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"TOTAL: {len(_results)}, FAILED: {len(fails)}")
    sys.exit(1 if fails else 0)


asyncio.run(main())
