# -*- coding: utf-8 -*-
"""文书校对引擎单元测试（纯函数，八维 + 法条时效）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from doc_review import review_document  # noqa: E402
import citations  # noqa: E402

results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def mods(rep):
    return {i["module"] for i in rep["issues"]}


# 构造一份满是瑕疵的委托代理合同片段
FLAWED = """委托代理合同

甲方（委托人）：＿＿＿＿＿＿＿＿某某有限公司

一、甲方特委托北京正阳律师事务所指派律师代理，乙方接受委托。
根据《合同法》第52条、《合同法》第107条，双方就委托代理事宜达成如下条款。
二、甲方应于本合同签订后向乙方支付订金人民币壹拾万元整（¥10,000元）。
三、乙方服务期限自2026年5月1日至2026年4月1日。
四、双方权力义务以本合同第99条约定为准，于2026年13月8日前完成交接。
第0１条 本合同一式两份。

（此处略）
"""
rep = review_document(FLAWED)
found = mods(rep)

record("M1 模板残留（空栏线/某某/此处略）", "M1 模板残留" in found and rep["stats"]["by_module"]["M1 模板残留"] >= 3,
       f"{rep['stats']['by_module'].get('M1 模板残留', 0)} 项")
record("M2 称呼一致（甲方未定义）", "M2 称呼一致" in found)
record("M3 法条格式（简称未用全称）", "M3 法条格式" in found and
       any("全称" in i["message"] for i in rep["issues"]))
record("M3 法条格式（阿拉伯条号转汉字建议）",
       any("第一百零七条" in i["suggestion"] or "第五十二条" in i["suggestion"] for i in rep["issues"]),
       [i["suggestion"] for i in rep["issues"] if "立法技术规范" in i["message"]][:1])
record("M4 金额一致（壹拾万 vs 10,000）", "M4 金额一致" in found,
       [i["message"] for i in rep["issues"] if i["module"] == "M4 金额一致"][:1])
record("M5 术语误用（订金/权力义务）", "M5 术语误用" in found and
       any("订金" in i["message"] for i in rep["issues"]) and
       any("权利义务" in i["message"] for i in rep["issues"]))
record("M6 日期逻辑（起止倒置）", any("倒置" in i["message"] for i in rep["issues"]))
record("M6 日期逻辑（13月不存在）", any("不存在日期" in i["message"] for i in rep["issues"]))
record("M7 交叉引用（第99条未定义）", any("第99条" in i["message"] for i in rep["issues"]))
record("M8 标点格式（全角数字）", any("全角数字" in i["message"] for i in rep["issues"]))
record("CIT 法条时效（合同法废止—NPC/本地）", any(i["module"] == "CIT 法条时效" and "已废止" in i["message"] for i in rep["issues"]),
       [i["message"] for i in rep["issues"] if i["module"] == "CIT 法条时效"][:1])

# 干净文书：零问题
CLEAN = """委托代理合同

甲方（委托人）：恒信贸易有限公司
乙方（受托方）：北京正阳律师事务所

一、依据《中华人民共和国民法典》第九百一十九条，甲方委托乙方代理与京泰物流有限公司的仓储合同纠纷一案。
二、代理费为人民币100,000元（大写：壹拾万元整），甲方应于2026年9月1日前支付至乙方账户。
三、委托期限自2026年5月1日起至2026年12月31日止。
"""
rep2 = review_document(CLEAN)
severe2 = [i for i in rep2["issues"] if i["severity"] == "严重"]
record("干净文书零严重问题", len(severe2) == 0,
       [f"{i['module']}:{i['message'][:30]}" for i in severe2][:3])
record("干净文书不误报订金/全称", not any("全称" in i["message"] or "订金" in i["message"] for i in rep2["issues"]),
       [i["message"][:40] for i in rep2["issues"] if "全称" in i["message"] or "订金" in i["message"]])

# 空文本
record("空文本", review_document("")["stats"]["chars"] == 0)

# ── 2026-09 回归：万元级金额、带空格日期、带空格/中文条号 ──

# M4 正确万元文书必须零误报（回归：曾因剥掉「万」把 385 万算成 385 元并误报）
OK_MONEY = "货款总额为人民币叁佰捌拾伍万元整（￥3,850,000 元）。"
rep3 = review_document(OK_MONEY, check_citations=False)
record("M4 万元级正确金额零误报", not any(i["module"].startswith("M4") for i in rep3["issues"]),
       [i["message"] for i in rep3["issues"] if i["module"].startswith("M4")])

# M4 万元级量级正确（提示文案应显示 100,000 而非 10）
rep4 = review_document("报酬为壹拾万元整。", check_citations=False)
m4 = [i for i in rep4["issues"] if i["module"].startswith("M4")]
record("M4 万元级量级正确", bool(m4) and "100,000" in m4[0]["message"], m4[0]["message"] if m4 else "未命中")

# M6 带空格的年月日也要识别
rep5 = review_document("本案于 2026 年 2 月 30 日立案。", check_citations=False)
record("M6 带空格日期", any("不存在日期" in i["message"] for i in rep5["issues"]),
       [i["message"] for i in rep5["issues"]])

# M6 横线日期也要识别
rep6 = review_document("本案于2026-02-30立案。", check_citations=False)
record("M6 横线格式日期", any("不存在日期" in i["message"] for i in rep6["issues"]),
       [i["message"] for i in rep6["issues"]])

# M7 带空格条号 + 中文数字条号都要识别
rep7 = review_document("详见本合同第 9 条。第一条 定义。", check_citations=False)
record("M7 带空格条号", any("第9条" in i["message"] for i in rep7["issues"]),
       [i["message"] for i in rep7["issues"]])

rep8 = review_document("详见本合同第九条。第一条 定义。", check_citations=False)
record("M7 中文数字条号", any("第9条" in i["message"] for i in rep8["issues"]),
       [i["message"] for i in rep8["issues"]])

# M7 已定义的引用不得误报
rep9 = review_document("详见本合同第二条。第一条 定义。第二条 价款。", check_citations=False)
record("M7 已定义不误报", not any(i["module"].startswith("M7") for i in rep9["issues"]),
       [i["message"] for i in rep9["issues"] if i["module"].startswith("M7")])

# M3 带空格阿拉伯条号也要提示改写
rep10 = review_document("依据民法典第 584 条。", check_citations=False)
record("M3 带空格阿拉伯条号", any("第 584 条" in i["message"] for i in rep10["issues"]),
       [i["message"] for i in rep10["issues"] if i["module"].startswith("M3")])

print()
failed = [n for n, ok in results if not ok]
print(f"{'=' * 40}\n{len(results) - len(failed)}/{len(results)} passed" + (f"，failed: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
