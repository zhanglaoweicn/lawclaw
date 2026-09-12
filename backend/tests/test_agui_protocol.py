# -*- coding: utf-8 -*-
"""AG-UI 协议合规性测试：对照官方 ag-ui 规范验证事件流。

官方规则（ag-ui/sdks/typescript/packages/core/src/events.ts + docs/concepts/events.mdx）：
1. 每个事件带 type；可选 timestamp(ms)
2. RUN_STARTED 必须含 threadId + runId，且是首个事件
3. run 以 RUN_FINISHED 或 RUN_ERROR 结束（互斥）
4. RUN_ERROR 的 message 为顶层字符串
5. STEP_STARTED/FINISHED 必须含 stepName
6. TOOL_CALL_START 必须含 toolCallId + toolCallName；TOOL_CALL_RESULT 必须含 messageId + content
7. 文本消息 Start → Content* → End 按 messageId 严格配对
"""
import asyncio
import json
import sys

import websockets

URI = "ws://127.0.0.1:9876"
results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def collect_stream(ws, timeout=180):
    """收集一个 chat run 的全部 agui 事件帧，直到收到 RPC 结果。"""
    events, result = [], None
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if msg.get("event") == "agui":
            events.append(msg["payload"])
        elif "result" in msg or "error" in msg:
            result = msg
            return events, result


async def main():
    async with websockets.connect(URI, max_size=30 * 1024 * 1024) as ws:
        hello = json.loads(await asyncio.wait_for(ws.recv(), 15))
        record("握手 ag_ui_version 0.2", hello.get("ag_ui_version") == "0.2",
               f"v={hello.get('ag_ui_version')}")

        await ws.send(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "chat",
            "params": {
                "message": "1+1等于几？只回答数字，不要检索。",
                "thread_id": "test-thread-agui",
            },
        }))
        events, result = await collect_stream(ws)
        types = [e.get("type") for e in events]

        # 1. 首事件 RUN_STARTED 且带 threadId + runId
        first_ok = events and events[0]["type"] == "RUN_STARTED" \
            and events[0].get("threadId") == "test-thread-agui" and events[0].get("runId")
        record("首事件 RUN_STARTED + threadId", bool(first_ok),
               f"types={types[:3]}… threadId={events[0].get('threadId') if events else None}")

        # 2. 所有事件带 timestamp(ms)
        ts_ok = all(isinstance(e.get("timestamp"), int) for e in events)
        record("全部事件带 timestamp(ms)", ts_ok)

        # 3. run 收尾：最后一个是 RUN_FINISHED 或 RUN_ERROR，且无另一种
        ends = [t for t in types if t in ("RUN_FINISHED", "RUN_ERROR")]
        end_ok = len(ends) == 1 and types[-1] == ends[0]
        record("RUN 收尾唯一且在末尾", end_ok, f"ends={ends}")

        # 4. STEP 事件带 stepName
        steps = [e for e in events if e["type"] in ("STEP_STARTED", "STEP_FINISHED")]
        step_ok = all(e.get("stepName") for e in steps)
        record("STEP 事件带 stepName", step_ok if steps else True, f"{len(steps)} 个 step 事件")

        # 5. TOOL_CALL_RESULT 带 messageId + content（若本次 run 用了工具）
        tcr = [e for e in events if e["type"] == "TOOL_CALL_RESULT"]
        tcr_ok = all(e.get("messageId") is not None and isinstance(e.get("content"), str) for e in tcr)
        record("TOOL_CALL_RESULT 带 messageId+content", tcr_ok if tcr else True, f"{len(tcr)} 个 result")

        # 6. RUN_ERROR 形态（错误路径：故意用无效 key）
        await ws.send(json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "chat",
            "params": {
                "message": "hi",
                "thread_id": "test-thread-err",
                "api_key": "sk-invalid-xyz",
                "base_url": "https://apihub.agnes-ai.com/v1",
                "model": "agnes-2.0-flash",
            },
        }))
        events2, _ = await collect_stream(ws, timeout=120)
        types2 = [e.get("type") for e in events2]
        errs = [e for e in events2 if e["type"] == "RUN_ERROR"]
        fin2 = [e for e in events2 if e["type"] == "RUN_FINISHED"]
        err_ok = len(errs) == 1 and isinstance(errs[0].get("message"), str) \
            and not fin2 and types2[-1] == "RUN_ERROR"
        record("错误路径 RUN_ERROR 顶层 message 且互斥", err_ok,
               f"message={errs[0].get('message', '')[:60] if errs else None}")

    print("\n===== SUMMARY =====")
    fails = [n for n, ok in results if not ok]
    for n, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"TOTAL: {len(results)}, FAILED: {len(fails)}")
    sys.exit(1 if fails else 0)


asyncio.run(main())
