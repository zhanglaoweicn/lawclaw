#!/usr/bin/env python3
"""统计中文文书的「字数」（Word 口径 = 汉字数 + 西文词数）与字符数。

字数上限类需求（如晨报 ≤400 字）交付前必跑：凭感觉估必然超。

用法：
    python count_zi.py 报告.md          # 读文件
    cat 报告.md | python count_zi.py    # 读标准输入
    python count_zi.py 报告.md 400      # 追加：对预算 400 字给出通过/超出结论（超时退出码 1）
"""
import re
import sys

HAN = re.compile(r"[\u4e00-\u9fff]")
WEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-:/]*")


def count(text: str) -> dict:
    han = HAN.findall(text)
    west = WEST.findall(text)
    return {
        "字数(Word口径)": len(han) + len(west),
        "汉字": len(han),
        "西文词": len(west),
        "字符数(不计空格)": len(re.sub(r"\s", "", text)),
    }


def main() -> int:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    stats = count(text)
    for key, val in stats.items():
        print(f"{key}: {val}")

    if len(sys.argv) > 2:
        budget = int(sys.argv[2])
        actual = stats["字数(Word口径)"]
        verdict = "通过" if actual <= budget else "超出"
        print(f"预算 {budget} 字 -> {actual} 字（{verdict}，差 {actual - budget:+d}）")
        return 0 if actual <= budget else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
