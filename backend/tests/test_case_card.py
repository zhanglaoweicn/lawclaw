# -*- coding: utf-8 -*-
"""判例卡抽取器单测：典型判决书 / 边界用例。"""
import sys
from pathlib import Path

BE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BE))

from case_card import extract_case_card  # noqa: E402

SAMPLE = """北京市第一中级人民法院
民事判决书

（2024）京01民终1234号

上诉人（原审被告）：北京某某贸易有限公司，住所地北京市海淀区。
被上诉人（原审原告）：张某某，男，1980年5月12日出生。

上诉人北京某某贸易有限公司因与被上诉人张某某买卖合同纠纷一案，
不服北京市海淀区人民法院（2023）京0108民初5678号民事判决，向本院提起上诉。
本院于2024年3月1日立案后，依法组成合议庭进行了审理。

本院认为：上诉人与被上诉人之间的买卖合同关系合法有效，被上诉人已依约交付货物，
上诉人未按约定支付货款构成违约，应当承担继续履行及赔偿损失的违约责任。
一审法院认定事实清楚，适用法律正确。上诉人的上诉请求不能成立，本院不予支持。

依照《中华人民共和国民事诉讼法》第一百七十七条第一款第一项之规定，判决如下：

驳回上诉，维持原判。

二审案件受理费13,800元，由上诉人北京某某贸易有限公司负担。

本判决为终审判决。

审 判 长  王某某
二〇二四年六月十八日
"""


def run():
    results = []

    # 1. 典型判决书：核心字段抽取
    card = extract_case_card(SAMPLE)
    results.append(("典型判决书 ok", card.get("ok") is True, str({k: card.get(k) for k in ('case_number', 'court', 'cause', 'confidence')})))
    results.append(("案号", card.get("case_number") == "（2024）京01民终1234号", str(card.get("case_number"))))
    results.append(("法院（首部优先）", card.get("court") == "北京市第一中级人民法院", str(card.get("court"))))
    results.append(("案由", card.get("cause") == "买卖合同纠纷", str(card.get("cause"))))
    results.append(("判决日期存在", card.get("judgment_date") is not None, str(card.get("judgment_date"))))

    # 2. 金额：判决主文里的“支付”金额
    sample2 = SAMPLE.replace("二审案件受理费13,800元，由上诉人北京某某贸易有限公司负担。",
                             "二、被告于本判决生效之日起十日内支付原告货款人民币1,250,000元；\n三、驳回原告其他诉讼请求。")
    card2 = extract_case_card(sample2)
    results.append(("主文金额 125万", card2.get("amount") == 1250000, str(card2.get("amount"))))

    # 3. “万元”单位
    sample3 = "（2025）沪01民终9号。本院认为……判决如下：被告赔偿原告经济损失50万元。上海市第一中级人民法院。判决日期2025年3月4日，本判决……"
    card3 = extract_case_card(sample3)
    results.append(("万元单位金额", card3.get("amount") == 500000, str(card3.get("amount"))))

    # 4. 非判决书：返回 ok=False 而非抛错
    card4 = extract_case_card("这是一份普通的会议记录，讨论了项目进度和下周安排，没有任何法律文书特征。" * 3)
    results.append(("非判决书 ok=False", card4.get("ok") is False, str(card4)))

    # 5. 空文本
    card5 = extract_case_card("")
    results.append(("空文本 ok=False", card5.get("ok") is False, str(card5)))

    # 6. 本院认为段抽取
    results.append(("裁判说理摘录", bool(card.get("reasoning") and "违约" in card["reasoning"]), str(card.get("reasoning", "")[:50])))

    # 7. 一审案号不干扰：主案号取第一个出现的（本案是二审案号）
    results.append(("主案号非一审引述", "民初" not in (card.get("case_number") or ""), str(card.get("case_number"))))

    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
    print(f"TOTAL: {passed}/{len(results)}")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
