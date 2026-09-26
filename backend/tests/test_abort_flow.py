# -*- coding: utf-8 -*-
"""中止机制回归测试（2026-09-26 全面修复迭代）。

覆盖两个 P0 修复：
1. abort 后同一 key 组合的后续 chat 不得被永久锁死为「已中止」
   （旧版 clear_abort 在早退 return 之后不可达）
2. 运行中 abort 必须真实生效（旧版 set_interrupt() 无参调用 TypeError 被吞）

用法：先启动 backend（runtime/Scripts/python.exe main.py --ws），再运行本文件。
"""
import asyncio
import json
import sys

import websockets

URI = "ws://127.0.0.1:9876"
_results = []


def record(name, ok, detail=""):
    _results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def rpc(ws, method, params=None, timeout=90):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"{method} timed out after {timeout}s")
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if msg.get("id") != 1:
            continue
        if "error" in msg:
            raise RuntimeError(f"{method} RPC error: {msg['error']}")
        return msg.get("result")


async def wait_run_end(ws, timeout=120):
    """等当前 run 收尾事件（RUN_FINISHED/RUN_ERROR）。"""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError("run did not finish in time")
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if msg.get("event") == "agui":
            t = msg.get("payload", {}).get("type", "")
            if t in ("RUN_FINISHED", "RUN_ERROR"):
                return t


async def main():
    async with websockets.connect(URI, max_size=20 * 1024 * 1024) as ws:
        await asyncio.wait_for(ws.recv(), timeout=15)
        await rpc(ws, "initialize", {})

        # ── 场景 1：空转 abort（无活动 run）→ 下一次 chat 必须正常执行 ──
        r = await rpc(ws, "abort", {})
        record("abort 无活动 run 返回 aborted", r.get("status") == "aborted", json.dumps(r, ensure_ascii=False)[:80])

        r = await rpc(ws, "chat", {"message": "只回答数字：1+1=?"})
        locked = "已中止" in (r.get("response") or "")
        record("空转 abort 后下一次 chat 不被锁死", not locked and r.get("response"),
               (r.get("response") or "")[:60])

        # ── 场景 2：运行中 abort → run 收尾，且后续 chat 正常（中断真实生效 + 事件被消费）──
        long_req = {"jsonrpc": "2.0", "id": 2, "method": "chat", "params": {
            "message": "请从合同解除、违约责任、诉讼时效、证据规则、保全担保五个角度，各写不少于 300 字的详细法律分析，不要省略。"}}
        await ws.send(json.dumps(long_req))
        got_delta = False
        # 等到开始流式输出再中止（确保 run 已真正开跑）
        deadline = asyncio.get_event_loop().time() + 90
        while not got_delta and asyncio.get_event_loop().time() < deadline:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
            if msg.get("type") == "delta" or (msg.get("event") == "agui"
                                              and msg.get("payload", {}).get("type") == "TEXT_MESSAGE_CONTENT"):
                got_delta = True
        record("长回复开始流式输出", got_delta)

        r = await rpc(ws, "abort", {})
        record("运行中 abort 接受", r.get("status") == "aborted")
        end_type = await wait_run_end(ws)
        record("被中止的 run 有收尾事件", end_type in ("RUN_FINISHED", "RUN_ERROR"), end_type)

        r = await rpc(ws, "chat", {"message": "只回答数字：2+2=?"})
        locked = "已中止" in (r.get("response") or "")
        record("运行中 abort 后后续 chat 不被锁死", not locked and r.get("response"),
               (r.get("response") or "")[:60])

    print("=" * 40)
    ok = sum(1 for _, p in _results if p)
    print(f"TOTAL: {ok}, FAILED: {len(_results) - ok}")
    sys.exit(0 if ok == len(_results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
