"""技能激活实证（单例版）：观察律师激活指定技能后 agent 的真实行为。

修正：唯一 request id + 发送前清残留帧（避免上一例的响应被当成本例结果）。
用法（后端需在 9876 运行）：runtime/Scripts/python.exe tests/_probe_skill_one.py <skill_id> <message>
"""
import asyncio
import json
import sys

import websockets

URI = "ws://127.0.0.1:9876"


async def drain(ws, seconds=0.4):
    """清掉遗留帧。"""
    while True:
        try:
            await asyncio.wait_for(ws.recv(), timeout=seconds)
        except Exception:
            return


async def run_case(ws, req_id, skill_id, message):
    print("=" * 70)
    print(f"技能: {skill_id}")
    print(f"提问: {message[:60]}…")
    tools, unknown, err, final = [], [], None, ""
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": req_id, "method": "chat", "params": {
        "message": message, "skill_id": skill_id, "thread_id": f"probe-{skill_id}-{req_id}"}}))
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=600))
        if msg.get("event") == "agui":
            ev = msg["payload"]
            t = ev.get("type")
            if t == "TOOL_CALL_START":
                tools.append(ev.get("toolCallName") or ev.get("toolName") or "")
            elif t == "TOOL_CALL_RESULT":
                c = str(ev.get("content") or "")
                if "Unknown tool" in c:
                    unknown.append(c[:160])
            elif t == "RUN_FINISHED":
                final = ev.get("finalResponse") or final
                break
            elif t == "RUN_ERROR":
                err = str(ev.get("message"))[:200]
                break
        elif msg.get("id") == req_id:
            if msg.get("error"):
                err = json.dumps(msg["error"], ensure_ascii=False)[:200]
            else:
                final = (msg.get("result") or {}).get("response") or final
            break
    print(f"  工具调用（{len(tools)}）:")
    for t in tools[:15]:
        print(f"     {t}")
    if unknown:
        print(f"  Unknown tool 报错（{len(unknown)}）: {unknown[:2]}")
    if err:
        print(f"  ERROR: {err}")
    print(f"  最终回复长度 {len(final)}；前 700 字:")
    print("    " + (final or "(空)").replace("\n", "\n    ")[:700])


async def main():
    skill_id = sys.argv[1] if len(sys.argv) > 1 else "employment-termination-review"
    message = sys.argv[2] if len(sys.argv) > 2 else (
        "公司想以「不能胜任工作」为由解除与员工的劳动合同，请审查是否合法。员工在职 3 年，签过两次固定期限合同。")
    async with websockets.connect(URI, max_size=20 * 1024 * 1024) as ws:
        await asyncio.wait_for(ws.recv(), timeout=15)
        await drain(ws)
        await run_case(ws, 7, skill_id, message)


if __name__ == "__main__":
    asyncio.run(main())
