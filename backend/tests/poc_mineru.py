# -*- coding: utf-8 -*-
"""MinerU 解析 PoC：复杂版式判决书（表格+多段落+手写区）的解析质量对比。

对照：pymupdf4llm（LawClaw 当前适配链首选）vs MinerU（RAG-Anything 的解析底座）。
评估维度：表格结构保留、标题层级、阅读顺序、字符召回率。

用法（需 .venv313 环境）：.venv313/Scripts/python.exe backend/tests/poc_mineru.py
"""
import io
import os
import sys

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mineru_poc")
PDF_PATH = os.path.join(OUT_DIR, "复杂判决书.pdf")


def make_complex_pdf() -> str:
    """生成带表格的复杂版式判决书（pymupdf 绘制表格线 + 双列当事人信息）。"""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()  # A4 595x842
    y = 60
    page.insert_text((72, y), "测试法院", fontname="china-s", fontsize=16)
    y += 24
    page.insert_text((72, y), "民  事  判  决  书", fontname="china-s", fontsize=14)
    y += 30
    page.insert_text((72, y), "TEST-2026-0001", fontname="china-s", fontsize=11)
    y += 26
    page.insert_text((72, y), "原告：测试当事人辰等32户业主。  被告：测试地产集团。",
                     fontname="china-s", fontsize=11)
    y += 30

    # ── 表格：诉讼请求与金额（表格线用线条绘制） ──
    table_top = y
    col_x = [72, 200, 340, 480]
    rows_y = [y, y + 22, y + 44, y + 66, y + 88]
    for ry in rows_y:
        page.draw_line((col_x[0], ry), (col_x[3], ry), width=0.7)
    for cx in col_x:
        page.draw_line((cx, rows_y[0]), (cx, rows_y[-1]), width=0.7)
    headers = ["诉讼请求", "金额（元）", "计算标准", "状态"]
    body_rows = [
        ["逾期交房违约金", "219,000", "日万分之五×730天", "支持"],
        ["购房款返还", "2,400,000", "合同解除条款", "部分支持"],
        ["利息损失", "158,700", "LPR×4年", "支持"],
    ]
    for ci, h in enumerate(headers):
        page.insert_text((col_x[ci] + 5, rows_y[0] + 15), h, fontname="china-s", fontsize=10)
    for ri, row in enumerate(body_rows, start=1):
        for ci, cell in enumerate(row):
            page.insert_text((col_x[ci] + 5, rows_y[ri] + 15), cell,
                             fontname="china-s", fontsize=10)
    y = rows_y[-1] + 34

    page.insert_text((72, y), "本院认为：开发商逾期交房构成根本违约，业主依合同约定解除合同。", fontname="china-s", fontsize=11)
    y += 20
    page.insert_text((72, y), "判决如下：一、解除购房合同；二、被告返还购房款并支付违约金合计2,777,700元。",
                     fontname="china-s", fontsize=11)
    y += 20
    page.insert_text((72, y), "案件受理费29,222元，由被告负担。", fontname="china-s", fontsize=11)

    os.makedirs(OUT_DIR, exist_ok=True)
    doc.save(PDF_PATH)
    doc.close()
    return PDF_PATH


def parse_with_pymupdf4llm() -> str:
    import pymupdf4llm
    return pymupdf4llm.to_markdown(PDF_PATH)


def parse_with_mineru() -> str:
    """调用 mineru CLI（应在 .venv313 内运行本脚本）。"""
    import subprocess
    env = dict(os.environ, MINERU_MODEL_SOURCE="modelscope")
    exe = os.path.join(os.path.dirname(sys.executable), "mineru.exe")
    if not os.path.exists(exe):
        exe = "mineru"
    r = subprocess.run(
        [exe, "-p", PDF_PATH, "-o", OUT_DIR],
        env=env, capture_output=True, text=True, timeout=540,
        cwd=OUT_DIR,
    )
    if r.returncode != 0:
        print("mineru stderr 末尾:", (r.stderr or "")[-500:])
        raise RuntimeError(f"mineru CLI 退出码 {r.returncode}")
    # 找输出 markdown
    for root, _, files in os.walk(OUT_DIR):
        for f in files:
            if f.endswith(".md"):
                return open(os.path.join(root, f), encoding="utf-8").read()
    raise RuntimeError("未找到 mineru 输出 markdown")


def score(name: str, text: str) -> dict:
    keys = ["219,000", "2,400,000", "158,700", "2,777,700", "29,222",
            "逾期交房违约金", "购房款返还", "利息损失", "日万分之五", "LPR",
            "本院认为", "测试地产集团", "TEST-2026-0001"]
    hits = [k for k in keys if k in text]
    has_table = ("|" in text) or ("表格" in text)
    return {
        "解析器": name,
        "字符数": len(text),
        "关键字命中": f"{len(hits)}/{len(keys)}",
        "缺失": [k for k in keys if k not in text][:6],
        "表格结构": "有" if has_table else "无",
    }


if __name__ == "__main__":
    path = make_complex_pdf()
    print(f"[0] 复杂测试判决书已生成: {path}")

    print("\n=== A. pymupdf4llm（当前适配链首选）===")
    a = parse_with_pymupdf4llm()
    import json
    print(json.dumps(score("pymupdf4llm", a), ensure_ascii=False, indent=2))

    print("\n=== B. MinerU（RAG-Anything 解析底座）===")
    try:
        b = parse_with_mineru()
        print(json.dumps(score("mineru", b), ensure_ascii=False, indent=2))
        open(os.path.join(OUT_DIR, "mineru_output.md"), "w", encoding="utf-8").write(b)
    except Exception as e:
        print("MinerU 解析失败:", str(e)[:300])

    print("\n输出目录:", OUT_DIR)
