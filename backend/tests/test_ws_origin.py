"""WS Origin 白名单验证：放行名单内的来源，拒绝任意网页来源。

用法（后端需在 9876 运行）：runtime/Scripts/python.exe <此文件>
"""
import asyncio
import json
import sys

import websockets

URI = "ws://127.0.0.1:9876"


async def try_connect(origin, label):
    try:
        async with websockets.connect(URI, origin=origin, open_timeout=10) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            ok = hello.get("event") == "ready"
            print(f"[{'PASS' if ok else 'FAIL'}] {label}: 放行（origin={origin}）")
            return True
    except Exception as e:
        print(f"[REJECTED] {label}: {type(e).__name__} — {str(e)[:80]}（origin={origin}）")
        return False


async def main():
    results = []
    # 应放行：Tauri WebView 与开发服务器来源
    results.append(("放行 localhost:1420", await try_connect("http://localhost:1420", "开发服务器")))
    results.append(("放行 tauri://localhost", await try_connect("tauri://localhost", "Tauri 生产来源")))
    # 应拒绝：任意网页
    rejected = await try_connect("https://evil.example.com", "恶意网页来源")
    results.append(("拒绝 evil.example.com", not rejected))

    print("=" * 40)
    ok = sum(1 for _, p in results if p)
    print(f"TOTAL: {ok}, FAILED: {len(results) - ok}")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
