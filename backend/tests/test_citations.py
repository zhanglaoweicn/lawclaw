# -*- coding: utf-8 -*-
"""法条引用抽取单元测试（纯函数，无后端依赖）。

覆盖 2026-09 引用可信度迭代的抽取规则：
多条并列 / 款项级 / 司法解释书名号 / 裸法名 / 废止标注 / 去重 / 跨句防误挂 / 中文数字 / 区间
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from citations import extract_citations  # noqa: E402

results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def pairs(text):
    return [(c["law"], c["article"]) for c in extract_citations(text)]


# 1. 多条并列：一个法名挂多条
cs = extract_citations("依据《民法典》第584条、第585条的规定，违约金过高可请求减少。")
record("多条并列抽取", pairs("依据《民法典》第584条、第585条的规定。") == [("民法典", "第584条"), ("民法典", "第585条")],
       str(pairs("依据《民法典》第584条、第585条的规定。")))

# 2. 款项级引用
cs = extract_citations("《民法典》第585条第2款规定，约定违约金……")
record("款项级 article", cs and cs[0]["article"] == "第585条第2款", cs[0]["article"] if cs else "无")

# 3. 司法解释书名号（含内嵌〈〉与序号后缀）
t = "依照《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（一）》第10条处理。"
cs = extract_citations(t)
ok = cs and cs[0]["law"].startswith("最高人民法院关于适用") and cs[0]["law"].endswith("解释（一）") and cs[0]["article"] == "第10条"
record("司法解释书名号", bool(ok), cs[0]["law"] if cs else "无")

# 4. 裸法名（无书名号）
record("裸法名抽取", pairs("根据民法典第585条的规定") == [("民法典", "第585条")],
       str(pairs("根据民法典第585条的规定")))

# 5. 已废止法律本地标注
cs = extract_citations("依据《合同法》第52条认定合同无效。")
ok = cs and cs[0].get("deprecated") is True and "民法典" in cs[0].get("replaced_by", "")
record("废止法律标注", bool(ok), cs[0].get("replaced_by", "") if cs else "无")

# 6. 按（法名,条号）去重：同一法条不同表述只出一张卡
n = len(extract_citations("《民法典》第585条是关于违约金的规定。实践中多依据民法典第585条调整违约金。"))
record("法条去重", n == 1, f"n={n}")

# 7. 跨句防误挂：句号后的"第N条"不挂到前一句法名
n = len(extract_citations("《民法典》施行后旧法废止。该条第2款另有约定的除外，第585条可参照。"))
ok = all(law != "民法典" or art == "第585条" for law, art in pairs("《民法典》施行后旧法废止。该条第2款另有约定的除外，第585条可参照。")) and \
     not any(a == "第585条" and l == "民法典" for l, a in pairs("《民法典》施行后旧法废止。该条第2款另有约定的除外，第585条可参照。"))
record("跨句不误挂", ok, str(pairs("《民法典》施行后旧法废止。该条第2款另有约定的除外，第585条可参照。")))

# 8. 中文数字条号
record("中文数字条号", pairs("依据《刑法》第二百六十四条的规定。") == [("刑法", "第二百六十四条")],
       str(pairs("依据《刑法》第二百六十四条的规定。")))

# 9. 区间引用：至/到连接的两个端点各出一条
record("区间引用端点", pairs("《民法典》第584条至第586条作了规定。") == [("民法典", "第584条"), ("民法典", "第586条")],
       str(pairs("《民法典》第584条至第586条作了规定。")))

# 10. 混合：多条+款项
record("混合多条款项",
       pairs("《民法典》第584条、第585条第1款以及第588条均……") ==
       [("民法典", "第584条"), ("民法典", "第585条第1款"), ("民法典", "第588条")],
       str(pairs("《民法典》第584条、第585条第1款以及第588条均……")))

# 11. 编章跳过：法名后先出现编/章标题，再出现条号
cs = extract_citations("《民法典》第三编合同第509条……")
record("编章后条号", cs and cs[0]["article"] == "第509条", cs[0]["article"] if cs else "无")

# 12. 空文本与无引用文本
record("空/无引用", extract_citations("") == [] and extract_citations("今天天气不错。") == [])

# 13. 法名归属不跨其他法名：裸条号只能挂给最近的法名
#     （回归：曾把「第65条」同时挂到《合同法解释（二）》《合同编通则解释》和裸「合同法」上，
#      产出杜撰式引用卡）
MIX = "《合同法解释（二）》第29条的“30%标准”已随合同法废止，现由《合同编通则解释》第65条替代。"
record("法名归属不跨法名", pairs(MIX) == [("合同法解释（二）", "第29条"), ("合同编通则解释", "第65条")],
       str(pairs(MIX)))

# 14. 同句两个同名法名各自持号，互不串挂
TWO = "依据《民法典》第584条，损失赔偿额应当相当于因违约造成的损失；《民法典》第585条允许调整过高违约金。"
record("同句两法名各自持号", pairs(TWO) == [("民法典", "第584条"), ("民法典", "第585条")], str(pairs(TWO)))

print()
failed = [n for n, ok in results if not ok]
print(f"{'=' * 40}\n{len(results) - len(failed)}/{len(results)} passed" + (f"，failed: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
