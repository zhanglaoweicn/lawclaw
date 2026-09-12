# -*- coding: utf-8 -*-
"""迭代1新功能验证：test_llm / 检索改写 / docx导出 / 技能中文名 / demo-mode 兜底"""
import asyncio
import json
import base64
import sys

import websockets

URI = "ws://127.0.0.1:9876"
results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def rpc(ws, method, params=None, timeout=60):
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}))
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - asyncio.get_event_loop().time())))
        if msg.get("id") != 1:
            continue
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get("result")


async def main():
    async with websockets.connect(URI, max_size=30 * 1024 * 1024) as ws:
        await asyncio.wait_for(ws.recv(), timeout=15)  # ready

        # 1. test_llm（真实调用，.env 现在是有效 Agnes key）
        r = await rpc(ws, "test_llm", {}, timeout=40)
        record("test_llm 真实连通", r.get("ok") is True, f"model={r.get('model')} {r.get('latency_ms')}ms")

        # 2. test_llm 错误本地化（假 key → 应返回中文提示而非英文堆栈）
        r = await rpc(ws, "test_llm", {"api_key": "sk-invalid-key-123", "base_url": "https://apihub.agnes-ai.com/v1", "model": "agnes-2.0-flash"}, timeout=40)
        msg = r.get("message", "")
        record("test_llm 错误中文化", r.get("ok") is False and "HTTP" in msg or "Key" in msg or "失败" in msg, msg[:80])

        # 3. 检索改写：口语化查询（此前 0 结果）
        r = await rpc(ws, "legal_search", {"query": "劳动合同到期不续签有补偿吗", "search_type": "law"}, timeout=60)
        n = len(r.get("results", []))
        record("检索改写-口语查询", n > 0, f"query_used={r.get('query_used', '')!r} rewritten={r.get('rewritten')} → {n}条")

        # 4. 规则改写：违约金过高
        r = await rpc(ws, "legal_search", {"query": "违约金过高如何调整", "search_type": "law"}, timeout=60)
        n = len(r.get("results", []))
        record("检索改写-违约金", n > 0, f"{n}条")

        # 5. export_docx
        md = "# 法律分析意见\n\n**结论**：违约金过高可请求法院适当减少。\n\n## 法条依据\n\n1. 《民法典》第585条\n2. 相关司法解释\n\n- 要点一：以实际损失为基础\n- 要点二：兼顾合同履行情况\n\n> 本分析仅供参考"
        r = await rpc(ws, "export_docx", {"title": "法律分析意见", "markdown": md, "matter_title": "测试案件"}, timeout=30)
        ok = r.get("ok") is True and len(r.get("data", "")) > 2000
        record("export_docx 导出", ok, f"{r.get('filename')} {len(r.get('data', ''))}B(base64)")
        if ok:
            open("test_export_sample.docx", "wb").write(base64.b64decode(r["data"]))

        # 6. 技能中文名
        r = await rpc(ws, "list_hermes_skills", {})
        skills = r.get("skills", [])
        ids = {s["id"] for s in skills}
        all_cn = all(not s["name"].startswith(("commercial-", "corporate-", "litigation-", "prc-")) for s in skills)
        record("技能中文名", len(skills) >= 20 and all_cn, f"{len(skills)}个技能，示例：{skills[0]['name'] if skills else 'N/A'}")

        # 7. demo-mode 兜底（假 key 走 chat 应回退 .env 成功）
        r = await rpc(ws, "chat", {"message": "1+1=?只回答数字", "api_key": "demo-mode"}, timeout=90)
        text = (r or {}).get("response", "")
        record("demo-mode 兜底", bool(text) and "未返回有效响应" not in text, text[:80])

    print("\n===== SUMMARY =====")
    fails = [n for n, ok in results if not ok]
    for n, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"TOTAL: {len(results)}, FAILED: {len(fails)}")
    sys.exit(1 if fails else 0)


asyncio.run(main())
