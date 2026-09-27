"""判例卡抽取器（B1 判例库地基）：从判决书全文抽取结构化字段。

纯函数模块——输入解析层产出的全文文本，输出：
    {ok, case_number, court, cause, amount, judgment_date, reasoning, confidence}

抽取失败时返回 {"ok": False}（不抛错——判例卡是增强信息，绝不能阻塞文档解析主链路）。
设计纪律：只抽"文本里明确写了"的字段，不做任何推断；置信度按证据强度分档。
"""
import re
from typing import Any, Dict

# 案号：（2024）京01民终1234号 / (2023)最高法民申456号 等
_CASE_NO_RE = re.compile(
    r"[（(]\s*(20\d{2}|19\d{2})\s*[）)]"      # 年份括号
    r"[^，。；！？\s（）()]{1,20}?"            # 法院代字/案件代字（非贪婪）
    r"第?\s*([0-9]{1,6}|[零一二三四五六七八九十百]+)\s*号"  # 序号（“第”可选——现行案号多数无“第”）
)
# 法院名：任意“……人民法院”（取判决书首部优先）
_COURT_RE = re.compile(r"([\u4e00-\u9fa5]{2,20}人民法院)")
# 案由：中国案由高度标准化——用关键词表从文本中定位（最长优先），避免抓到当事人名
_CAUSE_KEYWORDS = sorted({
    "民间借贷纠纷", "买卖合同纠纷", "商品房买卖合同纠纷", "房屋买卖合同纠纷",
    "房屋租赁合同纠纷", "建设工程施工合同纠纷", "建设工程合同纠纷", "装饰装修合同纠纷",
    "劳动争议", "工伤保险待遇纠纷", "追索劳动报酬纠纷", "经济补偿金纠纷",
    "机动车交通事故责任纠纷", "医疗损害责任纠纷", "生命权身体权健康权纠纷",
    "金融借款合同纠纷", "借款合同纠纷", "保证合同纠纷", "抵押合同纠纷", "质押合同纠纷",
    "融资租赁合同纠纷", "保理合同纠纷", "物业服务合同纠纷", "供热合同纠纷",
    "保管合同纠纷", "仓储合同纠纷", "委托合同纠纷", "承揽合同纠纷", "运输合同纠纷",
    "股权转让纠纷", "股东资格确认纠纷", "股东知情权纠纷", "公司决议纠纷",
    "损害公司利益责任纠纷", "请求变更公司登记纠纷", "清算责任纠纷",
    "商标权权属侵权纠纷", "侵害发明专利权纠纷", "侵害实用新型专利权纠纷",
    "著作权侵权纠纷", "侵害作品信息网络传播权纠纷", "侵害商业秘密纠纷",
    "不正当竞争纠纷", "垄断纠纷", "特许经营合同纠纷",
    "离婚纠纷", "离婚后财产纠纷", "抚养费纠纷", "变更抚养关系纠纷", "继承纠纷",
    "分家析产纠纷", "赡养费纠纷", "探望权纠纷",
    "租赁合同纠纷", "合同纠纷", "服务合同纠纷", "债权转让合同纠纷",
    "追偿权纠纷", "确认合同无效纠纷", "债权人代位权纠纷", "债权人撤销权纠纷",
    "侵权责任纠纷", "产品责任纠纷", "财产损害赔偿纠纷", "名誉权纠纷",
    "隐私权纠纷", "个人信息保护纠纷", "合伙合同纠纷",
}, key=len, reverse=True)
_CAUSE_LABELED_RE = re.compile(r"案由[：:]\s*([\u4e00-\u9fa5]{2,15}纠纷)")
_CAUSE_LOOSE_RE = re.compile(r"([\u4e00-\u9fa5]{2,15}纠纷)")
# 判决主文金额：赔偿/支付/偿还/给付/返还/退还 …… N 元（支持千分位逗号与“万元”）
_AMOUNT_RE = re.compile(
    r"(?:赔偿|支付|偿还|给付|返还|退还)"
    r"[^。；\n]{0,60}?"
    r"(?:人民币)?\s*([0-9][0-9,，]*(?:\.[0-9]{1,2})?)\s*(万元?)?"  # noqa: E501
)
# 判决日期：取全文最后一个“X年X月X日”
_DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
# 文末判决日期（中文数字）：“二〇二四年六月十八日”——判决书落款的标配格式
_CN_DATE_RE = re.compile(r"([二〇零一二三四五六七八九\d]{4})年([一二三四五六七八九十]{1,3})月([一二三四五六七八九十]{1,3})日")
_CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
# 本院认为段（裁判说理）：到“依照/据此/判决如下/之规定”为止
_REASONING_RE = re.compile(r"本院认为[：:]?(.{60,1500}?)(?=依照|据这|据此|判决如下|之规定)", re.S)


def _cn_num(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    if "十" not in s:
        return _CN_DIGITS.get(s, 0)
    a, _, b = s.partition("十")
    tens = _CN_DIGITS.get(a, 1) if a else 1
    ones = _CN_DIGITS.get(b, 0) if b else 0
    return tens * 10 + ones


def _cn_year(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    return int("".join(str(_CN_DIGITS.get(ch, 0)) for ch in s))


def _extract_cause(text: str) -> str | None:
    """案由定位：标注行 → 关键词表（最长优先）→ 宽匹配兜底。"""
    m = _CAUSE_LABELED_RE.search(text)
    if m:
        return m.group(1)
    for kw in _CAUSE_KEYWORDS:
        if kw in text:
            return kw
    m = _CAUSE_LOOSE_RE.search(text)
    return m.group(1) if m else None


def _to_number(num_str: str, unit_wan: bool) -> float | None:
    try:
        v = float(num_str.replace(",", "").replace("，", ""))
    except ValueError:
        return None
    return v * 10000 if unit_wan else v


def extract_case_card(text: str) -> Dict[str, Any]:
    """从判决书全文抽取结构化判例卡；无案号且无法院时视为非判决书。"""
    if not text or len(text) < 50:
        return {"ok": False, "reason": "文本过短"}
    try:
        card: Dict[str, Any] = {"ok": False, "confidence": "low"}

        m = _CASE_NO_RE.search(text)
        if m:
            card["case_number"] = m.group(0).replace(" ", "")
            card["year"] = m.group(1)

        courts = _COURT_RE.findall(text[:600]) or _COURT_RE.findall(text)
        if courts:
            card["court"] = courts[0]

        causes_result = _extract_cause(text)
        if causes_result:
            card["cause"] = causes_result

        # 判决主文金额：取“判决如下”之后的最大金额（避免把诉讼请求金额误当判决金额）
        body_start = text.find("判决如下")
        body = text[body_start:] if body_start >= 0 else text
        amounts = []
        for am in _AMOUNT_RE.finditer(body):
            s = am.group(1)
            unit = am.group(2) or ""
            v = _to_number(s, unit.startswith("万"))
            if v and v > 0:
                amounts.append(v)
        if amounts:
            card["amount"] = round(max(amounts), 2)

        dates = _DATE_RE.findall(text)
        if dates:
            y, mo, d = dates[-1]
            card["judgment_date"] = f"{y}-{int(mo):02d}-{int(d):02d}"
        # 中文数字落款日期（文末“二〇二四年六月十八日”）优先级更高——它是判决作出日
        cn_dates = _CN_DATE_RE.findall(text)
        if cn_dates:
            y, mo, d = cn_dates[-1]
            card["judgment_date"] = f"{_cn_year(y):04d}-{_cn_num(mo):02d}-{_cn_num(d):02d}"

        rm = _REASONING_RE.search(text)
        if rm:
            card["reasoning"] = re.sub(r"\s+", " ", rm.group(1)).strip()[:500]

        # 置信度：案号 + 法院齐备为 high；仅案号为 medium；其余 low
        if card.get("case_number") and card.get("court"):
            card["confidence"] = "high"
        elif card.get("case_number"):
            card["confidence"] = "medium"

        card["ok"] = bool(card.get("case_number") or card.get("court"))
        if not card["ok"]:
            card["reason"] = "未识别出案号或法院（可能不是判决书）"
        return card
    except Exception as e:  # 判例卡绝不阻塞解析主链路
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"[:120]}
