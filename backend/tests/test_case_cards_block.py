# -*- coding: utf-8 -*-
"""判例卡注入块单测：格式/空态/截断/金额格式化/防注入标记。"""
import sys
from pathlib import Path

BE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BE))
import os
os.environ.setdefault("HERMES_HOME", str(BE / ".hermes"))

from main import _build_case_cards_block  # noqa: E402

CARD = {
    "ok": True,
    "case_number": "（2024）京01民终1234号",
    "court": "北京市第一中级人民法院",
    "cause": "买卖合同纠纷",
    "amount": 1250000,
    "judgment_date": "2024-06-18",
    "reasoning": "上诉人未按约定支付货款构成违约。" * 30,  # 长 reasoning 触发截断
    "filename": "二审判决书.pdf",
    "confidence": "high",
}


def run():
    results = []

    # 1. 正常卡片
    block = _build_case_cards_block([CARD])
    results.append(("块非空", bool(block), f"{len(block)} 字"))
    results.append(("含案号", "（2024）京01民终1234号" in block, ""))
    results.append(("金额千分位格式", "¥1,250,000" in block, ""))
    results.append(("含使用说明", "真实判例" in block and "不构成对本案结果的承诺" in block, ""))
    results.append(("防注入框定", "不是用户指令" in block, ""))
    results.append(("文件名标注", "二审判决书.pdf" in block, ""))
    results.append(("reasoning 截断", "本院认为：" in block and len(block) < 1600, str(len(block))))

    # 2. 空态
    results.append(("空列表 → 空", _build_case_cards_block([]) == "", ""))
    results.append(("None → 空", _build_case_cards_block(None) == "", ""))
    results.append(("非列表 → 空", _build_case_cards_block("x") == "", ""))

    # 3. 非法条目跳过；全非法 → 空
    results.append(("非法条目跳过", _build_case_cards_block(["x", 123, None]) == "", ""))

    # 4. 超 6 张截断为 6 行
    many = [dict(CARD, case_number=f"（2024）京01民终{i}号") for i in range(9)]
    block_many = _build_case_cards_block(many)
    results.append(("9 张截断为 6", "（2024）京01民终7号" not in block_many, str(block_many.count("（2024）"))))

    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
    print(f"TOTAL: {passed}/{len(results)}")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
