# -*- coding: utf-8 -*-
"""文书细节校对引擎（纯函数模块，无副作用）。

八维机械规则 + 法条引用时效性验证（借鉴 community 文书细节校对 Skill 的 M1-M8 维度划分，
MIT 许可；本模块为面向 LawClaw 纯文本文书的自研实现）。

维度：
  M1 模板残留（严重）：占位符/待补标记/空栏线未清理
  M2 称呼一致（一般）：使用「甲方/乙方」但全文未定义对应当事人
  M3 法条格式（一般）：法律简称首次引用未用全称；条号使用阿拉伯数字（立法技术规范应汉字）
  M4 金额一致（一般）：中文大写金额在文中找不到等额数字金额
  M5 术语误用（严重/提示）：权力义务→权利义务、签定→签订、订金与定金之辨等
  M6 日期逻辑（严重）：起止日期倒置、不存在日（如 13 月/2 月 30 日）
  M7 交叉引用（提示）：「本合同第X条」在文中未找到对应条款定义
  M8 标点格式（一般）：全角数字混用
  CIT 法条时效（严重）：引用已废止/已修改法律（NPC 官方数据 + 本地废止表）

用法：
    from doc_review import review_document
    report = review_document(text)   # {"issues": [...], "stats": {...}}
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import citations
import npc_law

_SEVERITY_RANK = {"严重": 0, "一般": 1, "提示": 2}


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _mk(module: str, severity: str, message: str, suggestion: str,
        text: str, start: int, end: int = -1) -> Dict[str, Any]:
    end = end if end >= 0 else start
    return {
        "module": module,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
        "line": _line_of(text, start),
        "excerpt": text[max(0, start - 18):end + 22].replace("\n", " ").strip(),
    }


# ── M1 模板残留 ──────────────────────────────────────────────
_M1_PATTERNS = [
    (re.compile(r"[＿_]{3,}"), "空栏线「___」未填写"),
    (re.compile(r"×{2,}|Ｘ{2,}|XX+"), "「XX/×××」占位符未替换"),
    (re.compile(r"\[+\s*(?:PLACEHOLDER|待补[充填]?|填写|此处)[^\]]*\]+", re.I), "方括号待补标记"),
    (re.compile(r"【[^】]{0,12}(?:待补[充填]?|填写|此处|留空)[^】]{0,20}】"), "【】待补标记"),
    (re.compile(r"（此处[^）]{0,12}(?:略|省略)[^）]{0,6}）"), "「此处略」占位"),
    (re.compile(r"某某(?:公司|单位|人|律师事务所|律所)?"), "「某某」占位称谓"),
]


def m1_placeholders(text: str) -> List[Dict[str, Any]]:
    out = []
    for pat, why in _M1_PATTERNS:
        for m in pat.finditer(text):
            out.append(_mk("M1 模板残留", "严重", why,
                           "正式文书提交前必须替换/删除全部占位内容", text, m.start(), m.end()))
    return out


# ── M2 称呼一致 ──────────────────────────────────────────────
def m2_undefined_parties(text: str) -> List[Dict[str, Any]]:
    out = []
    for party in ("甲方", "乙方"):
        if re.search(party, text) and not re.search(party + r"\s*[（(：:]", text):
            m = re.search(party, text)
            out.append(_mk("M2 称呼一致", "一般", f"使用「{party}」但全文未定义对应当事人",
                           f"建议在首部定义，如「{party}（受托方）：××公司」", text, m.start(), m.end()))
    return out


# ── M3 法条格式 ──────────────────────────────────────────────
_M3_ABBR = {
    "民法典": "中华人民共和国民法典", "合同法": "中华人民共和国合同法", "民事诉讼法": "中华人民共和国民事诉讼法",
    "民诉法": "中华人民共和国民事诉讼法", "刑事诉讼法": "中华人民共和国刑事诉讼法",
    "刑诉法": "中华人民共和国刑事诉讼法", "行政诉讼法": "中华人民共和国行政诉讼法",
    "刑法": "中华人民共和国刑法", "劳动合同法": "中华人民共和国劳动合同法",
    "专利法": "中华人民共和国专利法", "商标法": "中华人民共和国商标法",
    "著作权法": "中华人民共和国著作权法", "公司法": "中华人民共和国公司法",
}
_M3_ARABIC = re.compile(r"第\s*(\d+)\s*([条款项])")


def m3_law_citation_format(text: str) -> List[Dict[str, Any]]:
    out = []
    full_seen: set = set()
    abbr_checked: set = set()
    for m in re.finditer("|".join(_M3_ABBR), text):
        name = m.group(0)
        if name in abbr_checked:
            continue
        abbr_checked.add(name)
        full = _M3_ABBR[name]
        if full not in text and full not in full_seen:
            out.append(_mk("M3 法条格式", "一般",
                           f"法律简称「{name}」首次引用未使用全称",
                           f"首次出现建议用「{full}」，其后可用简称", text, m.start(), m.end()))
        full_seen.add(full)
    for m in _M3_ARABIC.finditer(text):
        num = int(m.group(1))
        cn = citations.num_to_cn(num)
        suffix = m.group(2)
        out.append(_mk("M3 法条格式", "一般",
                       f"条号使用了阿拉伯数字「{m.group(0)}」",
                       f"按《立法技术规范》应写作「第{cn}{suffix}」", text, m.start(), m.end()))
    return out


# ── M4 金额一致 ──────────────────────────────────────────────
_CN_AMOUNT_DIGITS = {"零": 0, "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5,
                     "陆": 6, "柒": 7, "捌": 8, "玖": 9}
_CN_AMOUNT_UNITS = {"拾": 10, "佰": 100, "仟": 1000}
_CN_AMOUNT_BIG = {"万": 10000, "亿": 100000000}


def _cn_amount_to_value(cn: str) -> int | None:
    """中文大写金额数字部分 → 数值（壹拾万元 → 100000）。仅支持整数部分。"""
    total, section, num = 0, 0, None
    for ch in cn:
        if ch in _CN_AMOUNT_DIGITS:
            num = _CN_AMOUNT_DIGITS[ch]
        elif ch in _CN_AMOUNT_UNITS:
            if num is None:
                num = 1
            section += num * _CN_AMOUNT_UNITS[ch]
            num = None
        elif ch in _CN_AMOUNT_BIG:
            if num is not None:
                section += num
                num = None
            total = (total + section) * _CN_AMOUNT_BIG[ch]
            section = 0
        elif ch == "元":
            break
    if num is not None:
        section += num
    return total + section if (total or section) else None


_CN_AMOUNT_RE = re.compile(r"[壹贰叁肆伍陆柒捌玖][零壹贰叁肆伍陆柒捌玖拾佰仟万亿元整正]*")
_NUM_AMOUNT_RE = re.compile(r"([1-9][\d,，]*)(?:\.\d+)?\s*元")


def m4_amount_consistency(text: str) -> List[Dict[str, Any]]:
    out = []
    num_values = {int(m.group(1).replace(",", "").replace("，", "")) for m in _NUM_AMOUNT_RE.finditer(text)}
    for m in _CN_AMOUNT_RE.finditer(text):
        cn = m.group(0)
        # 只剥掉尾部单位字，保留「万/亿」——否则万元级金额被当成个位数量级，
        # 正确文书全部误报（且提示写成「约 385 元」）。
        digits = re.sub(r"[元整正]", "", cn)
        val = _cn_amount_to_value(digits)
        if val is None or val == 0:
            continue
        if val not in num_values:
            out.append(_mk("M4 金额一致", "一般",
                           f"大写金额「{cn}」（约 {val:,} 元）在文中未找到等额数字金额",
                           "请核对大写与数字金额是否一致（二者不一致时以大写为准）", text, m.start(), m.end()))
    return out


# ── M5 术语误用 ──────────────────────────────────────────────
_M5_RULES = [
    (re.compile(r"权力义务"), "「权力义务」应为「权利义务」", "严重", "民事关系中使用「权利」"),
    (re.compile(r"签定"), "「签定」应为「签订」", "一般", "规范用词为「签订」"),
    (re.compile(r"既使"), "「既使」应为「即使」", "一般", "规范用词为「即使」"),
    (re.compile(r"订金"), "「订金」与「定金」法律含义不同", "提示",
     "定金适用定金罚则（双倍返还/不予返还），订金一般视为预付款——请确认本意"),
    (re.compile(r"做出(?:决定|判决|裁定)"), "「做出决定/判决」应为「作出」", "提示", "裁判与决定类文书规范用「作出」"),
]


def m5_term_misuse(text: str) -> List[Dict[str, Any]]:
    out = []
    for pat, msg, sev, sug in _M5_RULES:
        for m in pat.finditer(text):
            out.append(_mk("M5 术语误用", sev, msg, sug, text, m.start(), m.end()))
    return out


# ── M6 日期逻辑 ──────────────────────────────────────────────
# 允许年月日之间出现空格（实务文书常见「2026 年 2 月 30 日」）
_D = r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
_M6_RANGE = re.compile(
    rf"自?\s*{_D}\s*(?:起)?\s*(?:至|到|～|~|—|--)\s*{_D}")
_M6_STANDALONE = re.compile(_D)
_M6_DASHED = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


def _valid_ymd(y: int, mo: int, d: int) -> bool:
    import datetime
    try:
        datetime.date(y, mo, d)
        return True
    except ValueError:
        return False


def m6_date_logic(text: str) -> List[Dict[str, Any]]:
    out = []
    for m in _M6_RANGE.finditer(text):
        y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
        if (y1, mo1, d1) > (y2, mo2, d2):
            out.append(_mk("M6 日期逻辑", "严重",
                           f"起止日期倒置：{y1}-{mo1}-{d1} 晚于 {y2}-{mo2}-{d2}",
                           "核对起止日期先后顺序", text, m.start(), m.end()))
    for m in _M6_STANDALONE.finditer(text):
        y, mo, d = map(int, m.groups())
        if not (1 <= mo <= 12 and 1 <= d <= 31 and _valid_ymd(y, mo, d)):
            out.append(_mk("M6 日期逻辑", "严重",
                           f"不存在日期「{y}年{mo}月{d}日」",
                           "核对日历有效性", text, m.start(), m.end()))
    for m in _M6_DASHED.finditer(text):
        y, mo, d = map(int, m.groups())
        if not (1 <= mo <= 12 and 1 <= d <= 31 and _valid_ymd(y, mo, d)):
            out.append(_mk("M6 日期逻辑", "严重",
                           f"不存在日期「{y}-{mo:02d}-{d:02d}」",
                           "核对日历有效性", text, m.start(), m.end()))
    return out


# ── M7 交叉引用 ──────────────────────────────────────────────
# 条号可能是阿拉伯数字、中文数字，或「第 9 条」这类带空格写法
_ARTICLE_NUM = r"[0-9一二三四五六七八九十百千零]+"
_ANY_ARTICLE = re.compile(rf"第\s*({_ARTICLE_NUM})\s*条")
_M7_REF = re.compile(rf"本(?:合同|协议|办法|规定)\s*第\s*({_ARTICLE_NUM})\s*条")

_CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def _article_num_to_int(s: str) -> int | None:
    """条号 → 整数（「15」/「十五」/「一百二十」）。"""
    if s.isdigit():
        return int(s)
    section, num, ok = 0, 0, False
    for ch in s:
        if ch in _CN_NUM:
            num = _CN_NUM[ch]
            ok = True
        elif ch in _CN_UNIT:
            section += (num or 1) * _CN_UNIT[ch]
            num = 0
            ok = True
        elif ch == "零":
            continue
        else:
            return None
    return section + num if ok else None


def m7_cross_reference(text: str) -> List[Dict[str, Any]]:
    out = []
    counts: Dict[int, int] = {}
    for m in _ANY_ARTICLE.finditer(text):
        v = _article_num_to_int(m.group(1))
        if v is not None:
            counts[v] = counts.get(v, 0) + 1
    for m in _M7_REF.finditer(text):
        n = _article_num_to_int(m.group(1))
        if n is None:
            continue
        # 交叉引用处本身也含「第X条」，故定义处应使同号出现 ≥2 次
        if counts.get(n, 0) < 2:
            out.append(_mk("M7 交叉引用", "提示",
                           f"「本合同第{n}条」在文中未找到对应条款定义",
                           f"核对内部条款编号或补齐第{n}条", text, m.start(), m.end()))
    return out


# ── M8 标点格式 ──────────────────────────────────────────────
_M8_FULLWIDTH_NUM = re.compile(r"[０-９]+")


def m8_punctuation(text: str) -> List[Dict[str, Any]]:
    out = []
    for m in _M8_FULLWIDTH_NUM.finditer(text):
        out.append(_mk("M8 标点格式", "一般", "使用了全角数字",
                       "正式文书统一使用半角阿拉伯数字", text, m.start(), m.end()))
    return out


# ── CIT 法条时效（NPC 官方 + 本地废止表） ─────────────────────
def citation_validity(text: str, max_checks: int = 8) -> List[Dict[str, Any]]:
    out = []
    cites = citations.extract_citations(text)
    checked = 0
    for c in cites:
        law = c["law"]
        if c.get("deprecated"):
            out.append(_mk("CIT 法条时效", "严重",
                           f"引用已废止法律「{law}」",
                           f"已于 {c.get('effective_until')} 废止，替代：{c.get('replaced_by')}",
                           text, 0, 1))
            continue
        if checked >= max_checks:   # 限流保护：一次校对最多查 8 部法律
            continue
        checked += 1
        try:
            npc = npc_law.find_law_status(law)
        except Exception:
            continue
        if not npc:
            continue
        if npc["sxx"] == 1:
            out.append(_mk("CIT 法条时效", "严重",
                           f"引用已废止法律「{law}」",
                           f"官方状态：已废止（公布 {npc['gbrq']}）——请改用现行有效法律",
                           text, 0, 1))
        elif npc["sxx"] == 2:
            out.append(_mk("CIT 法条时效", "提示",
                           f"「{law}」存在修正版本",
                           f"官方状态：已修改（现行版本施行 {npc['sxrq']}）——请按现行版本核对条文", text, 0, 1))
    return out


# ── 汇总入口 ─────────────────────────────────────────────────
def review_document(text: str, check_citations: bool = True) -> dict:
    if not text or not text.strip():
        return {"issues": [], "stats": {"chars": 0, "lines": 0, "by_module": {}, "by_severity": {}}}
    checks = [
        m1_placeholders(text), m2_undefined_parties(text), m3_law_citation_format(text),
        m4_amount_consistency(text), m5_term_misuse(text), m6_date_logic(text),
        m7_cross_reference(text), m8_punctuation(text),
    ]
    if check_citations:
        checks.append(citation_validity(text))
    issues = [i for chk in checks for i in chk]
    issues.sort(key=lambda i: (i["line"], _SEVERITY_RANK.get(i["severity"], 3)))
    by_module: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    for i in issues:
        by_module[i["module"]] = by_module.get(i["module"], 0) + 1
        by_severity[i["severity"]] = by_severity.get(i["severity"], 0) + 1
    return {
        "issues": issues,
        "stats": {
            "chars": len(text), "lines": text.count("\n") + 1,
            "by_module": by_module, "by_severity": by_severity,
        },
    }
