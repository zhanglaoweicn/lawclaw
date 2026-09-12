# -*- coding: utf-8 -*-
"""PoC：LightRAG 案件知识库（借鉴 RAG-Anything 评估的检索底座验证）。

验证目标：
1. 判决书 PDF → doc_intel 抽取 → LightRAG 图谱构建（LLM 中文实体抽取）
2. 中文混合检索（hybrid/local/global）能否正确回答判决内容
3. 管线在 429 限流环境下的耐受性

环境妥协（诚实声明）：
- embedding 用本地哈希向量（jieba bigram → 256 维）——Agnes hub 无 embedding 端点、
  Ollama 未安装。排序质量弱于真语义向量，本 PoC 只验证"管线 + 抽取 + 图谱"，不验证语义排序。
"""
import asyncio
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 读 .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".rag_poc")
os.makedirs(WORK_DIR, exist_ok=True)


def make_test_pdf() -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    body = (
        "测试法院\n民事判决书\n\n"
        "原告：测试委托人巳。被告：测试相对方午建设工程有限公司。\n\n"
        "本院认为：双方签订的《借款合同》合法有效。被告未按期归还借款本金500万元，构成违约。"
        "利息按年利率12%计算，未超过一年期贷款市场报价利率四倍，本院予以支持。\n\n"
        "判决如下：一、被告于本判决生效后十日内偿还原告借款本金500万元及相应利息；"
        "二、驳回原告其他诉讼请求。\n\n"
        "如不服本判决，可在判决书送达之日起十五日内提起上诉。"
    )
    page.insert_text((72, 90), body, fontname="china-s", fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── 本地哈希 embedding（jieba bigram → 256 维，零依赖） ──
import hashlib

_DIM = 256

def _hash_embed(texts: list[str]) -> list[list[float]]:
    out = []
    for t in texts:
        vec = [0.0] * _DIM
        t = (t or "").lower()
        try:
            import jieba
            toks = jieba.lcut(t)
        except Exception:
            toks = [t[i:i + 2] for i in range(max(0, len(t) - 1))]
        toks = [x for x in toks if x.strip()]
        for tok in toks + [t[i:i + 2] for i in range(max(0, len(t) - 1))]:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % _DIM] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        out.append([v / norm for v in vec])
    return out


async def aembed(texts: list[str]):
    import numpy as np
    return np.array(_hash_embed(texts))   # LightRAG 存储层期望 ndarray（.size 属性）


# ── LLM：Agnes chat completions，带 429 重试 ──
async def allm(prompt: str, **kwargs) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", ""),
        timeout=120,
    )
    last_err = None
    for attempt in range(4):
        try:
            resp = await client.chat.completions.create(
                model=os.environ.get("LAWCLAW_MODEL", "agnes-2.0-flash"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                wait = 25 * (attempt + 1)
                print(f"    [限流] 等待 {wait}s 后重试（{attempt + 1}/4）")
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError(f"LLM 调用最终失败: {last_err}")


async def main():
    from doc_intel import extract_document_text
    pdf_text = extract_document_text("判决书.pdf", make_test_pdf())
    assert pdf_text["ok"], "PDF 抽取失败"
    print(f"[1] 判决书抽取 OK（{pdf_text['chars']} 字符，解析器 {pdf_text['extractor']}）")

    from lightrag import LightRAG, QueryParam
    from lightrag.utils import EmbeddingFunc

    rag = LightRAG(
        working_dir=WORK_DIR,
        llm_model_func=allm,
        llm_model_name=os.environ.get("LAWCLAW_MODEL", "agnes-2.0-flash"),
        embedding_func=EmbeddingFunc(embedding_dim=_DIM, max_token_size=4000, func=aembed),
    )
    await rag.initialize_storages()   # 1.5.7：管线命名空间需显式初始化

    print("[2] 图谱构建中（LLM 中文实体抽取，可能多次调用 + 限流重试）...")
    t0 = time.time()
    await rag.ainsert(pdf_text["text"])
    print(f"    构建完成，耗时 {time.time() - t0:.0f}s")

    questions = [
        ("hybrid", "被告需要偿还的借款本金是多少？"),
        ("local", "利息按什么标准计算？"),
        ("global", "被告违反了什么义务？"),
    ]
    print("[3] 中文检索问答验证：")
    passed = 0
    for mode, q in questions:
        try:
            ans = await rag.aquery(q, param=QueryParam(mode=mode))
            ok = ("500" in ans) or ("违约" in ans and mode != "local") or ("利率" in ans and mode == "local")
            passed += ok
            print(f"    [{mode}] {'PASS' if ok else 'WEAK'} Q={q}")
            print(f"        A={ans[:150].strip()}")
        except Exception as e:
            print(f"    [{mode}] ERROR: {str(e)[:120]}")
    print(f"\n===== PoC 结果: {passed}/3 问回答正确 =====")


if __name__ == "__main__":
    asyncio.run(main())
