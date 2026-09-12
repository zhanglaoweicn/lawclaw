# -*- coding: utf-8 -*-
"""法条引用抽取（纯函数模块：无副作用、可被单元测试直接导入）。

从 AI 回复文本中抽取"《法律》第N条"式引用，供前端 CitationCard 展示与
verify_citation（元典）验证；已废止法律（DEPRECATED_LAWS）直接本地标注。

抽取规则（2026-09 引用可信度迭代）：
- 通用书名号法名：《……法/解释/条例/规定/办法/意见/细则/修正案（一）》——覆盖司法解释与行政法规
- 裸法名白名单（无书名号的常用简称，如"根据民法典第585条"）
- 同一句内一个法名可挂多条法条（"第584条、第585条"各出一条引用）
- 法条标记支持 款/项 后缀（第585条第2款）；引用窗口不跨句，防止把下一句的"第N条"误挂
- 按（法名, 条号）去重：同一法条不同表述只出一张卡
"""
import re

DEPRECATED_LAWS = {
    # 民法典吸收的 9 部法律
    "合同法": {"replaced_by": "民法典（第三编 合同）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典合同编"},
    "物权法": {"replaced_by": "民法典（第二编 物权）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典物权编"},
    "担保法": {"replaced_by": "民法典（物权编担保物权 + 合同编保证合同）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，担保物权整合至物权编，保证合同整合至合同编"},
    "侵权责任法": {"replaced_by": "民法典（第七编 侵权责任）", "effective_until": "2020-12-31",
                    "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典侵权责任编"},
    "婚姻法": {"replaced_by": "民法典（第五编 婚姻家庭）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典婚姻家庭编"},
    "收养法": {"replaced_by": "民法典（第五编 婚姻家庭·收养章节）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典婚姻家庭编收养章节"},
    "继承法": {"replaced_by": "民法典（第六编 继承）", "effective_until": "2020-12-31",
                "note": "《民法典》2021年1月1日生效时废止，相关内容整合至民法典继承编"},
    # 合同法前身（1999年合同法实施时废止）
    "经济合同法": {"replaced_by": "合同法（已废止）→ 民法典", "effective_until": "1999-09-30",
                    "note": "1999年《合同法》实施时废止；2021年《合同法》又被《民法典》吸收"},
    "涉外经济合同法": {"replaced_by": "合同法（已废止）→ 民法典", "effective_until": "1999-09-30",
                        "note": "1999年《合同法》实施时废止；2021年《合同法》又被《民法典》吸收"},
    "技术合同法": {"replaced_by": "合同法（已废止）→ 民法典", "effective_until": "1999-09-30",
                    "note": "1999年《合同法》实施时废止；2021年《合同法》又被《民法典》吸收"},
}


# 法条标记：第N条，可选 第N款/第N项 后缀（款项前必须先有条）
_ARTICLE_MARKER = re.compile(
    r'第[一二三四五六七八九十百千万零\d]+条'
    r'(?:第[一二三四五六七八九十百千万零\d]+款)?'
    r'(?:第[一二三四五六七八九十百千万零\d]+项)?'
)

# 通用书名号法名：名称以 法/解释/条例/规定/办法/意见/细则/修正案 结尾（允许（一）类序号后缀）
_QUOTED_LAW = re.compile(
    r'《([^《》]{2,40}?(?:法|解释|条例|规定|办法|意见|细则|修正案)(?:（[一二三四五六七八九十\d]+）)?)》'
)

# 裸法名（无书名号）白名单——沿用历史常用法律简称表
_BARE_LAW_RE = re.compile('(?:' + "民法典|民事诉讼法|刑法|刑事诉讼法|行政诉讼法|公司法|合同法|劳动合同法|著作权法|专利法|商标法|反不正当竞争法|担保法|物权法|侵权责任法|保险法|票据法|海商法|仲裁法|律师法|公证法|收养法|继承法|婚姻法|个人所得税法|企业所得税法|税收征收管理法|预算法|审计法|统计法|中国人民银行法|商业银行法|证券法|信托法|基金法|保险法|海南自由贸易港法|香港特别行政区维护国家安全法|反分裂国家法|国防法|兵役法|军事设施保护法|国防动员法|国防教育法|人民防空法|现役军官法|预备役军官法|军官军衔条例|立法法|监督法|全国人民代表大会组织法|国务院组织法|人民法院组织法|人民检察院组织法|地方各级人民代表大会和地方各级人民政府组织法|民族区域自治法|澳门特别行政区基本法|香港特别行政区基本法|反垄断法|反洗钱法|环境保护法|大气污染防治法|水污染防治法|固体废物污染环境防治法|噪声污染防治法|土壤污染防治法|环境影响评价法|节约能源法|可再生能源法|清洁生产促进法|循环经济促进法|野生动物保护法|森林法|草原法|渔业法|矿产资源法|土地管理法|城市房地产管理法|建筑法|安全生产法|消防法|道路交通安全法|海上交通安全法|民用航空法|铁路法|邮政法|烟草专卖法|农业法|农业技术推广法|种子法|动物防疫法|农产品质量安全法|食品安全法|药品管理法|传染病防治法|国境卫生检疫法|母婴保健法|献血法|执业医师法|人口与计划生育法|体育法|教育法|义务教育法|高等教育法|职业教育法|民办教育促进法|科学技术进步法|科学技术普及法|文物保护法|非物质文化遗产法|国家通用语言文字法|工会法|红十字会法|慈善法|残疾人保障法|未成年人保护法|预防未成年人犯罪法|老年人权益保障法|妇女权益保障法|消费者权益保护法" + ')')

_SENTENCE_STOP = set('。！？；;\n\r')


def _window(text: str, start: int, limit: int = 120) -> str:
    """取法名之后的本句片段（不跨句），供多条法条抽取；最多 limit 字符。"""
    seg = text[start:start + max(0, limit)]
    for i, ch in enumerate(seg):
        if ch in _SENTENCE_STOP:
            return seg[:i]
    return seg


def _next_law_start(law_spans, after: int):
    """返回 after 之后最近的一个法名起点（无则 None）。"""
    cands = [s for s, _e in law_spans if s >= after]
    return min(cands) if cands else None


def extract_citations(text: str) -> list:
    """从文本抽取法条引用列表。

    返回元素结构（与历史版本兼容）：
        {law, article, content, source, [deprecated, replaced_by, effective_until, deprecation_note]}
    """
    if not text:
        return []
    citations = []
    seen = set()

    def add(law: str, article: str, start: int, end: int):
        key = (law, article)
        if key in seen:
            return
        seen.add(key)
        citation = {
            "law": law,
            "article": article,
            "content": text[start:end].strip()[:80],
            "source": "AI生成",
        }
        # 本地标注已废止法律（无需调用元典 API）
        if law in DEPRECATED_LAWS:
            dep = DEPRECATED_LAWS[law]
            citation["deprecated"] = True
            citation["replaced_by"] = dep["replaced_by"]
            citation["effective_until"] = dep["effective_until"]
            citation["deprecation_note"] = dep["note"]
        citations.append(citation)

    # 先收集全部法名位置（书名号法名 + 不在书名号内的裸法名），供窗口截断用
    quoted = list(_QUOTED_LAW.finditer(text))
    quoted_spans = [(m.start(), m.end()) for m in quoted]
    bare = [m for m in _BARE_LAW_RE.finditer(text)
            if not any(s <= m.start() < e for s, e in quoted_spans)]
    law_spans = [(m.start(), m.end()) for m in quoted] + [(m.start(), m.end()) for m in bare]

    def collect(m, is_quoted: bool):
        """把该法名之后「同一句、且不跨其他法名」的条号全部计入。

        窗口必须止于下一个法名——否则「《合同法解释（二）》…现由《合同编通则解释》第65条」
        会把第 65 条同时挂到两个法名上，产出杜撰式引用（律师端比"没有卡片"更糟）。
        """
        law = m.group(1) if is_quoted else m.group(0)
        start = m.end()
        nxt = _next_law_start(law_spans, start)
        limit = 120 if nxt is None else min(120, nxt - start)
        for am in _ARTICLE_MARKER.finditer(_window(text, start, limit)):
            add(law, am.group(0), m.start(), start + am.end())

    # ① 通用书名号法名 ② 裸法名白名单
    for m in quoted:
        collect(m, True)
    for m in bare:
        collect(m, False)

    return citations

# 中文数字（立法技术规范口径）
_CN_DIGITS = "零一二三四五六七八九"


def num_to_cn(n: int, combined: bool = False) -> str:
    """整数 → 中文数字。combined=True（处于更高位组合中）时 10-19 写「一十X」：
    917 → 九百一十七；独立语境 10 → 十、17 → 十七。"""
    if n <= 0:
        return str(n)
    if n < 10:
        return _CN_DIGITS[n]
    if n == 10:
        return "一十" if combined else "十"
    if n < 20:
        return ("一十" if combined else "十") + _CN_DIGITS[n % 10]
    if n < 100:
        return _CN_DIGITS[n // 10] + "十" + (_CN_DIGITS[n % 10] if n % 10 else "")
    if n < 1000:
        head = _CN_DIGITS[n // 100] + "百"
        rem = n % 100
        if rem == 0:
            return head
        if rem < 10:
            return head + "零" + _CN_DIGITS[rem]
        return head + num_to_cn(rem, combined=True)
    return str(n)
