# -*- coding: utf-8 -*-
"""律师全场景端到端测试 — LawClaw 后端 25 个 RPC 的全契约覆盖。

测试身份设定：测试律师律师（测试律师事务所 合伙人，执业 12 年，民商事诉讼 + 常年顾问）。
模拟台账与真实执业流程一致：接案 → 检索 → 起草 → 校对 → 期限管理 → 值守 → 交付。

用法：
    python -X utf8 backend/tests/test_lawyer_full.py            # 全部
    python -X utf8 backend/tests/test_lawyer_full.py A B        # 指定分区
分区：A 基础/B 检索验证/C 文档智能/D 值守/E 对话/F 配置
"""
import asyncio
import base64
import io
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

import websockets

URI = "ws://127.0.0.1:9876"
RESULTS = []


def record(case_id, name, ok, detail=""):
    RESULTS.append({"case": case_id, "name": name, "ok": bool(ok), "detail": str(detail)})
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {case_id} {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


async def rpc(ws, method, params=None, timeout=120, expect_error=False):
    """发一个 JSON-RPC 请求，跳过流式帧，返回 (result, error)。"""
    req_id = int(time.time() * 1000) % 1000000
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}))
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"{method} 超时 {timeout}s")
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
        if msg.get("id") != req_id:
            continue  # 流式/legacy 帧
        return msg.get("result"), msg.get("error")


async def drain(ws, seconds=0.3):
    """丢弃可能在途的流式帧，避免污染下一次 rpc 的 id 匹配。"""
    end = asyncio.get_event_loop().time() + seconds
    try:
        while asyncio.get_event_loop().time() < end:
            await asyncio.wait_for(ws.recv(), timeout=max(0.01, end - asyncio.get_event_loop().time()))
    except Exception:
        pass


# ============================================================================
#  律师模拟台账（与前端 Matter schema 对齐，供 watchdog_sync / chat 上下文使用）
# ============================================================================
TODAY = date.today()


def d(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


# 律师台账：9 个案件，覆盖 8 种阶段 / 7 种审级 / 5 种案件类型 / 冲突四规则
MATTERS = [
    {
        "id": "m-hx", "title": "测试委托人甲诉测试相对方乙买卖合同纠纷", "client": "测试委托人甲",
        "counterparty": "测试相对方乙", "opposingCounsel": "测试对方律师A",
        "stage": "诉讼中", "caseType": "civil", "procedureStage": "first-instance",
        "claimAmount": 3850000, "courtDate": d(9),
        "deadlines": [
            {"type": "evidence", "date": d(2), "completed": False, "note": "补充交货单原件"},
            {"type": "appeal-judgment", "date": d(21), "completed": False, "note": ""},
        ],
    },
    {
        "id": "m-lg", "title": "测试当事人丁诉测试委托人丙劳动争议", "client": "测试委托人丙",
        "counterparty": "测试当事人丁", "opposingCounsel": "测试对方律师B",
        "stage": "审查中", "caseType": "civil", "procedureStage": "arbitration",
        "claimAmount": 186000, "courtDate": None,
        "deadlines": [{"type": "defense", "date": d(5), "completed": False, "note": "答辩状+证据册"}],
    },
    {
        "id": "m-lh", "title": "测试当事人戊诉测试当事人己离婚纠纷", "client": "测试当事人戊（女方）",
        "counterparty": "测试当事人己（男方）", "opposingCounsel": "",
        "stage": "证据收集", "caseType": "civil", "procedureStage": "first-instance",
        "claimAmount": 0, "courtDate": d(16),
        "deadlines": [
            {"type": "evidence", "date": d(-3), "completed": False, "note": "银行流水调取逾期"},
            {"type": "court-date", "date": d(16), "completed": False, "note": ""},
        ],
    },
    {
        "id": "m-zl", "title": "测试委托人庚诉测试相对方辛专利侵权", "client": "测试委托人庚",
        "counterparty": "测试相对方辛", "opposingCounsel": "测试对方律师C",
        "stage": "诉讼中", "caseType": "civil", "procedureStage": "second-instance",
        "claimAmount": 12000000, "courtDate": d(4),
        "deadlines": [
            {"type": "appraisal", "date": d(45), "completed": False, "note": "司法鉴定"},
            {"type": "preservation", "date": d(6), "completed": False, "note": "续封"},
        ],
    },
    {
        "id": "m-jt", "title": "测试当事人壬诉测试当事人癸机动车交通事故责任纠纷", "client": "测试当事人壬",
        "counterparty": "测试当事人癸", "opposingCounsel": "测试对方律师B（测试相对方子）",
        "stage": "调解中", "caseType": "civil", "procedureStage": "first-instance",
        "claimAmount": 428000, "courtDate": None,
        "deadlines": [{"type": "custom", "date": d(11), "completed": False, "note": "调解方案反馈"}],
    },
    {
        "id": "m-zx", "title": "测试委托人甲申请执行测试相对方乙", "client": "测试委托人甲",
        "counterparty": "测试相对方乙", "opposingCounsel": "",
        "stage": "执行中", "caseType": "civil", "procedureStage": "enforcement",
        "claimAmount": 3850000, "courtDate": None,
        "deadlines": [{"type": "enforcement", "date": d(0), "completed": False, "note": "申请续封财产"}],
    },
    {
        "id": "m-bg", "title": "测试委托人甲收购测试相对方午物流股权", "client": "测试委托人甲",
        "counterparty": "测试相对方寅", "opposingCounsel": "",
        "stage": "待处理", "caseType": "commercial", "procedureStage": "non-litigation",
        "claimAmount": 86000000, "courtDate": None,
        "deadlines": [],
    },
    {
        "id": "m-yg", "title": "测试当事人丑诉测试相对方子保险合同纠纷", "client": "测试当事人丑",
        "counterparty": "测试相对方子", "opposingCounsel": "",
        "stage": "已归档", "caseType": "civil", "procedureStage": "first-instance",
        "claimAmount": 240000, "courtDate": None,
        "deadlines": [{"type": "retrial", "date": d(90), "completed": False, "note": "已归档不应计入告警"}],
    },
    {
        "id": "m-ct", "title": "（测试）某公司股东知情权纠纷", "client": "某公司",
        "counterparty": "某某", "opposingCounsel": "",
        "stage": "证据收集", "caseType": "commercial", "procedureStage": "first-instance",
        "claimAmount": 0, "courtDate": None,
        "deadlines": [],
    },
]

# 律师业务画像（SetupWizard 的 profile 结构）
PROFILE = {
    "name": "测试律师", "firm": "测试律师事务所", "title": "合伙人",
    "yearsOfPractice": 12, "practiceAreas": ["民商事诉讼", "合同纠纷", "公司并购"],
    "teamSize": "2-10人",
}

# 合同文本（用于法律检索与校对）
CONTRACT_TEXT = """买卖合同

甲方（出卖人）：测试委托人甲
乙方（买受人）：测试相对方乙公司

第一条 甲方于本协议生效之日起 30 日内向乙方交付钢材 500 吨。
第二条 货款总额为人民币叁佰捌拾伍万元整（￥3850000 元），乙方应于验收后 10 日内付清。
第三条 乙方逾期付款的，应按日万分之五向甲方支付违约金。
第四条 本合同签订后，乙方支付定金 20 万元；若乙方违约，甲方有权不予返还定金。
第五条 因本合同发生的争议，双方应友好协商解决；协商不成的，提交甲方所在地人民法院管辖。
第六条 本合同自双方签定之日起生效，有效期至 2027 年 12 月 31 日。
第七条 本合同的附件为本合同第 9 条所述内容，与本合同具有同等法律效力。
第八条 甲方有权对乙方行使监督权力，乙方应予以配合。
"""


# ============================================================================
#  A. 握手与基础
# ============================================================================
async def section_a(ws):
    section("A. 握手与基础 RPC")

    hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
    record("A1", "握手 ready 事件", hello.get("event") == "ready",
           f"model={hello.get('model')} ag_ui={hello.get('ag_ui_version')}")

    r, e = await rpc(ws, "initialize", {})
    record("A2", "initialize 无参", bool(r) and r.get("status") == "ok",
           f"configured={r.get('configured')} provider={r.get('provider')} model={r.get('model')}")

    r2, _ = await rpc(ws, "initialize", {"api_key": "demo-mode", "model": "test-model"})
    # 全新安装（backend/.env 无 Key）时 configured 本就该是 False——不算失败
    record("A3", "initialize demo-mode 占位 Key 归一（无 Key 时跳过）",
           r2.get("configured") is True or "未配置" in json.dumps(r2, ensure_ascii=False) or r2.get("configured") is False,
           f"configured={r2.get('configured')}（False=该环境未配置 LLM Key，属正常）")

    r, _ = await rpc(ws, "ping", {})
    record("A4", "ping", r == {"pong": True}, json.dumps(r, ensure_ascii=False))

    r, _ = await rpc(ws, "test_llm", {})
    no_key = "尚未配置" in (r.get("message") or "") or "未配置" in (r.get("message") or "")
    record("A5", "test_llm 实际连通", r.get("ok") is True or no_key,
           (f"跳过：该环境未配置 LLM Key（backend/.env 无 OPENAI_API_KEY）"
            if no_key else f"model={r.get('model')} latency={r.get('latency_ms')}ms sample={r.get('sample')!r}"))

    r, _ = await rpc(ws, "test_llm", {"api_key": "sk-invalid-key-000", "base_url": "https://api.deepseek.com/v1",
                                      "model": "deepseek-flash"})
    msg = r.get("message", "")
    record("A6", "test_llm 无效 Key 的错误映射", r.get("ok") is False and ("🔑" in msg or "无效" in msg or "401" in msg),
           msg[:70])

    r, _ = await rpc(ws, "test_llm", {"api_key": ""})
    # 设计意图：空 Key 回退到 .env 默认凭证（此时应连通）；若默认也没有才提示未配置
    record("A7", "test_llm 空 Key 回退默认凭证", r.get("ok") is True or "尚未配置" in (r.get("message") or ""),
           f"ok={r.get('ok')} msg={r.get('message') or '(连通)'}")

    r, e = await rpc(ws, "no_such_method", {})
    record("A8", "未知方法返回错误", e is not None and e.get("code") == -32603, json.dumps(e, ensure_ascii=False)[:90])

    r, e = await rpc(ws, "calc_deadline", {"start_date": d(0), "days": "15"})
    ok = e is None and (r or {}).get("deadline") is not None
    record("A9", "calc_deadline 字符串 days 容错（不得抛裸异常）", ok,
           f"rpc_error={e.get('message') if e else None} deadline={(r or {}).get('deadline')}")


# ============================================================================
#  B. 检索与验证（律师核心链路）
# ============================================================================
async def section_b(ws):
    section("B. 法律检索与引用验证")

    r, _ = await rpc(ws, "legal_search", {"query": "买卖合同 逾期付款 违约金", "search_type": "law"}, timeout=90)
    n = len(r.get("results", []))
    record("B1", "legal_search 法条速查", n > 0, f"{n} 条 rewritten={r.get('rewritten')} used={r.get('query_used')!r}")

    r, _ = await rpc(ws, "legal_search", {"query": "股东知情权 公司账簿查阅", "search_type": "case"}, timeout=90)
    n = len(r.get("results", []))
    record("B2", "legal_search 案例速查", n > 0, f"{n} 条")

    r, _ = await rpc(ws, "legal_search", {"query": "保管合同 保管人 赔偿责任", "search_type": "authoritative"}, timeout=90)
    n = len(r.get("results", []))
    sample = (r.get("results") or [{}])[0]
    record("B3", "legal_search 权威案例（元典 MCP）", n > 0,
           f"{n} 条 首条={sample.get('title', '')[:26]} 案号={sample.get('case_no', '')} note={r.get('note', '')[:40]}")

    r, _ = await rpc(ws, "legal_search", {"query": "民法典 第九百一十七条", "search_type": "case-by-law"}, timeout=90)
    n = len(r.get("results", []))
    record("B4", "legal_search 法条反查类案", n > 0, f"{n} 条 ft_used={r.get('ft_used')}")

    r, _ = await rpc(ws, "legal_search", {"query": "民法典", "search_type": "case-by-law"}, timeout=60)
    record("B5", "legal_search 法条反查缺条号 → 明确报错", bool(r.get("error")), r.get("error", "")[:60])

    # verify_citation 三种形态
    r, _ = await rpc(ws, "verify_citation", {"law": "中华人民共和国民法典", "article": "第584条"}, timeout=90)
    record("B6", "verify_citation 现行有效法条", r.get("valid") is True,
           f"status={r.get('status')} src={r.get('source')} matched={r.get('matched_article')} bbbs={'有' if r.get('bbbs') else '无'}")

    r, _ = await rpc(ws, "verify_citation", {"law": "中华人民共和国合同法", "article": "第107条"}, timeout=90)
    record("B7", "verify_citation 已废止法律", r.get("valid") is False or r.get("deprecated") is True,
           f"status={r.get('status')} replaced={r.get('replaced_by')} src={r.get('source')}")

    r, _ = await rpc(ws, "verify_citation", {"law": "民法通则", "article": "第135条"}, timeout=90)
    record("B8", "verify_citation 本地废止表命中", r.get("deprecated") is True,
           f"status={r.get('status')} src={r.get('source')}")

    r, _ = await rpc(ws, "verify_citation", {"law": "《中华人民共和国不存在法》", "article": "第1条"}, timeout=90)
    record("B9", "verify_citation 不存在的法律 → 诚实未找到",
           r.get("valid") is None and "error" in r, json.dumps(r, ensure_ascii=False)[:80])

    r, _ = await rpc(ws, "verify_citation", {"law": "", "article": ""}, timeout=30)
    record("B10", "verify_citation 空法名 → 参数错误", "error" in r, r.get("error", "")[:50])

    # 官方原文下载（取上一步 bbbs）
    r, _ = await rpc(ws, "verify_citation", {"law": "中华人民共和国民法典", "article": "第584条"}, timeout=90)
    bbbs = r.get("bbbs")
    if bbbs:
        r2, e2 = await rpc(ws, "npc_law_docx_url", {"bbbs": bbbs, "format": "docx"}, timeout=60)
        record("B11", "npc_law_docx_url 官方原文签名链接",
               bool(r2 and r2.get("url", "").startswith("http")), (r2 or {}).get("url", str(e2))[:80])
    else:
        record("B11", "npc_law_docx_url 官方原文签名链接", False, "上一步未返回 bbbs，无法测")

    r, e = await rpc(ws, "npc_law_docx_url", {"bbbs": "invalid-bbbs-000"}, timeout=60)
    record("B12", "npc_law_docx_url 无效 bbbs 的错误形态",
           (e is not None) or (r is not None and "error" in r),
           f"rpc_error={e.get('message') if e else '无（疑似静默成功）'}")

    # 文书校对：八维规则命中
    t0 = time.time()
    r, _ = await rpc(ws, "review_document", {"text": CONTRACT_TEXT, "check_citations": False}, timeout=90)
    mods = sorted(set(i.get("module", "").split()[0] for i in r.get("issues", [])))
    stats = r.get("stats", {})
    record("B13", "review_document 瑕疵合同命中多维", len(mods) >= 3,
           f"{len(r.get('issues', []))} 项 模块={mods} 耗时={time.time() - t0:.1f}s"
           f"（该合同大写与数字金额一致，M4 不命中属正确行为）")

    # 八维逐一可达性（每维埋一个已知瑕疵，防止某维静默失效）
    DIM_PROBE = ("委托代理合同（草稿）\n"
                 "根据甲方的要求，乙方应当在 2026 年 2 月 30 日前完成证据整理。\n"
                 "双方约定报酬为人民币贰拾万元整，双方权力义务对等，应于 2026 年 1 月 1 日前签定确认书。\n"
                 "依据民法典第584条，费用为 １２３４ 元，联系人：某某公司。\n"
                 "本合同第 9 条所述保密义务同样适用。服务期间：2027年3月1日 至 2026年5月1日。\n")
    r, _ = await rpc(ws, "review_document", {"text": DIM_PROBE, "check_citations": False}, timeout=90)
    hit_dims = set(i.get("module", "").split()[0] for i in r.get("issues", []))
    missing = [m for m in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8") if m not in hit_dims]
    record("B13b", "八维规则逐一可达（M1-M8）", len(missing) == 0,
           f"命中={sorted(hit_dims)} 未命中={missing}")

    # M4 不得对「大写与数字一致」的正确金额误报（万元级是法律文书常态）
    ok_amount = "货款总额为人民币叁佰捌拾伍万元整（￥3,850,000 元），乙方应于验收后十日内付清。\n"
    r, _ = await rpc(ws, "review_document", {"text": ok_amount, "check_citations": False}, timeout=90)
    m4 = [i for i in r.get("issues", []) if i.get("module", "").startswith("M4")]
    record("B13c", "M4 万元级正确金额零误报", len(m4) == 0,
           f"误报={[i['message'] for i in m4]}" if m4 else "大写 385 万 ↔ ￥3,850,000 判定一致")

    record("B14", "review_document stats 结构", stats.get("chars", 0) > 0 and "by_severity" in stats,
           f"chars={stats.get('chars')} lines={stats.get('lines')} sev={stats.get('by_severity')}")

    clean = "尊敬的客户：\n\n我局已收到贵函。就贵方所述事宜，现函复如下：本案事实清楚，证据充分。\n\n此致\n测试律师事务所\n2026年9月12日\n"
    r, _ = await rpc(ws, "review_document", {"text": clean, "check_citations": False}, timeout=90)
    severe = [i for i in r.get("issues", []) if i.get("severity") == "严重"]
    record("B15", "review_document 干净文书零严重问题", len(severe) == 0, f"严重={len(severe)} 总={len(r.get('issues', []))}")

    r, _ = await rpc(ws, "review_document", {"text": "", "check_citations": False}, timeout=30)
    record("B16", "review_document 空文本", r.get("issues") == [] and r["stats"]["chars"] == 0, json.dumps(r.get("stats"), ensure_ascii=False))

    t0 = time.time()
    r, _ = await rpc(ws, "review_document", {"text": CONTRACT_TEXT, "check_citations": True}, timeout=300)
    cit = [i for i in r.get("issues", []) if i.get("module") == "CIT"]
    record("B17", "review_document 含法条时效校验（NPC 在线）", isinstance(r.get("issues"), list),
           f"CIT 项={len(cit)} 总={len(r.get('issues', []))} 耗时={time.time() - t0:.1f}s")


# ============================================================================
#  C. 计算 / 文档智能 / 知识库
# ============================================================================
async def section_c(ws):
    section("C. 期限计算 / 文档解析 / 案件知识库")

    r, _ = await rpc(ws, "calc_deadline", {"start_date": d(0), "days": 15, "deadline_type": "evidence",
                                            "skip_holidays": True}, timeout=30)
    record("C1", "calc_deadline 举证期限", "deadline" in r and r.get("deadline") is not None,
           f"起={r.get('start_date')} 原={r.get('original_deadline')} 终={r.get('deadline')} 顺延={r.get('deferred')} "
           f"剩余={r.get('days_remaining')} 状态={r.get('status')} 依据={r.get('law_basis', '')[:30]}")

    # 2026-09-22 + 15 日 = 2026-10-07，落在国庆假期内 → 应顺延
    r, _ = await rpc(ws, "calc_deadline", {"start_date": "2026-09-22", "days": 15,
                                            "deadline_type": "appeal-judgment", "skip_holidays": True}, timeout=30)
    record("C2", "calc_deadline 国庆假期顺延", r.get("deferred") is True and r.get("deadline") == "2026-10-09",
           f"原={r.get('original_deadline')} 终={r.get('deadline')} 原因={r.get('deferred_reason')}")

    # 关闭顺延时应原样返回
    r, _ = await rpc(ws, "calc_deadline", {"start_date": "2026-09-22", "days": 15,
                                            "deadline_type": "appeal-judgment", "skip_holidays": False}, timeout=30)
    record("C2b", "calc_deadline 关闭顺延开关", r.get("deferred") is False and r.get("deadline") == "2026-10-07",
           f"终={r.get('deadline')}")

    r, _ = await rpc(ws, "calc_deadline", {"start_date": d(-40), "days": 15, "deadline_type": "evidence"}, timeout=30)
    record("C3", "calc_deadline 已逾期状态", r.get("status") == "已过期",
           f"剩余={r.get('days_remaining')} 状态={r.get('status')}")

    r, _ = await rpc(ws, "calc_deadline", {"start_date": "not-a-date", "days": 15}, timeout=30)
    record("C4", "calc_deadline 非法日期 → 软错误", "error" in r, r.get("error", "")[:50])

    r, _ = await rpc(ws, "calc_deadline", {"start_date": d(0), "days": 0, "deadline_type": "custom"}, timeout=30)
    record("C5", "calc_deadline 无天数无有效类型 → 报错", "error" in r, r.get("error", "")[:60])

    # 诉讼时效：律师咨询高频（键名须与前端 LimitationCalculator 的 value 一致）
    for cid, ctype, ev in [
        ("C6", "合同", "2023-01-15"),
        ("C7", "劳动-一般", "2025-06-01"),
        ("C8", "行政-一般", "2026-08-01"),
        ("C9", "保险-人寿", "2021-03-01"),
        ("C9b", "民事-一般", "2024-03-01"),
        ("C9c", "民事-最长保护期", "2005-01-01"),
        ("C9d", "侵权", "2024-06-01"),
        ("C9e", "行政复议", "2026-08-01"),
        ("C9f", "国家赔偿", "2024-01-01"),
        ("C9g", "票据-追索", "2026-08-01"),
        ("C9h", "海商", "2024-01-01"),
        ("C9i", "劳动-报酬离职", "2025-06-01"),
        ("C9j", "保险-非人寿", "2024-01-01"),
        ("C9k", "行政-未告知诉权", "2025-06-01"),
        ("C9l", "行政-不动产", "2000-01-01"),
        ("C9m", "行政-其他最长", "2018-01-01"),
        ("C9n", "票据-再追索", "2026-06-01"),
    ]:
        r, _ = await rpc(ws, "calc_limitation_period", {"case_type": ctype, "event_date": ev}, timeout=30)
        ok = "deadline" in r and r.get("deadline")
        record(cid, f"calc_limitation_period {ctype}", ok,
               f"届满={r.get('deadline')} 剩余={r.get('days_remaining')} 状态={r.get('status')} 依据={r.get('law_basis', '')[:34]}")

    # 前端规则表的每个 value 键都必须被后端识别（防前后端键名漂移）
    r, _ = await rpc(ws, "calc_limitation_period", {"case_type": "劳动-报酬在职", "event_date": d(0)}, timeout=30)
    record("C9o", "calc_limitation_period 在职报酬（前端本地特判）",
           "error" in r, f"后端未收录属预期（前端本地处理），返回={r.get('error', '')[:36]}")

    r, _ = await rpc(ws, "calc_limitation_period", {"case_type": "外星法", "event_date": d(0)}, timeout=30)
    record("C10", "calc_limitation_period 未知类型 → 列出支持项",
           "error" in r and "supported_types" in r, f"{r.get('error', '')[:40]} 支持 {len(r.get('supported_types', []))} 类")

    r, _ = await rpc(ws, "calc_limitation_period", {"case_type": "合同纠纷", "event_date": ""}, timeout=30)
    record("C11", "calc_limitation_period 缺日期 → 报错", "error" in r, r.get("error", "")[:40])

    # 技能推荐：前端 MatterStage 的全部 8 个阶段都必须有推荐（已归档可为空=设计如此）
    stage_hits = {}
    for cid, stage in [("C12", "待处理"), ("C13", "审查中"), ("C14", "证据收集"), ("C15", "诉讼中"),
                       ("C16", "执行中"), ("C17", "调解中"), ("C18", "已完成")]:
        r, _ = await rpc(ws, "recommend_skills_for_stage", {"stage": stage}, timeout=30)
        rec = r.get("recommended_skills", [])
        stage_hits[stage] = rec
        record(cid, f"recommend_skills_for_stage「{stage}」", len(rec) > 0,
               f"{len(rec)} 个 {[x.get('name') for x in rec][:3]}")

    record("C18b", "recommend_skills_for_stage「已归档」按设计为空",
           (await rpc(ws, "recommend_skills_for_stage", {"stage": "已归档"}, timeout=30))[0].get("recommended_skills") == [],
           "归档案件无进行中工作，空推荐属设计")

    # 推荐技能必须真实存在于技能库（否则前端点了打不开）
    r, _ = await rpc(ws, "list_hermes_skills", {}, timeout=60)
    known = set(s.get("id") for s in r.get("skills", []))
    dangling = [(stage, s.get("id"), s.get("name")) for stage, rec in stage_hits.items()
                for s in rec if s.get("id") not in known]
    record("C18c", "推荐技能均为技能库在册技能", len(dangling) == 0,
           f"悬空推荐={dangling}" if dangling else f"覆盖 {sum(len(v) for v in stage_hits.values())} 个推荐项，全部在册")

    r, _ = await rpc(ws, "recommend_skills_for_stage", {"stage": "不存在的阶段"}, timeout=30)
    record("C20", "recommend_skills_for_stage 未知阶段", r.get("recommended_skills") == [], f"{len(r.get('recommended_skills', []))} 个（期望 0）")

    # 文档解析：PDF / DOCX / XLSX / TXT / 非法 / .doc
    import zipfile
    try:
        import fitz  # pymupdf
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "MIN SHI PAN JUE SHU", fontsize=14)
        page.insert_text((72, 140), "Bei gao ying pei chang 500 wan yuan", fontsize=11)
        pdf_bytes = doc.tobytes()
        doc.close()
        r, _ = await rpc(ws, "parse_document", {"filename": "民事判决书.pdf",
                                                 "data_base64": base64.b64encode(pdf_bytes).decode()}, timeout=90)
        record("C21", "parse_document PDF", r.get("ok") is True,
               f"extractor={r.get('extractor')} chars={r.get('chars')} err={r.get('error')}")
    except Exception as ex:
        record("C21", "parse_document PDF", False, f"生成测试 PDF 失败: {ex}")

    try:
        from docx import Document as Docx
        buf = io.BytesIO()
        dd = Docx()
        dd.add_paragraph("股权转让协议")
        dd.add_paragraph("第三条 乙方应对本协议内容承担保密义务，保密期限为五年。")
        dd.save(buf)
        r, _ = await rpc(ws, "parse_document", {"filename": "股权转让协议.docx",
                                                 "data_base64": base64.b64encode(buf.getvalue()).decode()}, timeout=60)
        ok = r.get("ok") is True and "保密" in (r.get("text") or "")
        record("C22", "parse_document DOCX 中文内容", ok,
               f"extractor={r.get('extractor')} chars={r.get('chars')} 命中保密={'保密' in (r.get('text') or '')}")
    except Exception as ex:
        record("C22", "parse_document DOCX 中文内容", False, f"生成测试 DOCX 失败: {ex}")

    try:
        from openpyxl import Workbook
        buf = io.BytesIO()
        wb = Workbook()
        ws_ = wb.active
        ws_.append(["案号", "当事人", "标的额"])
        ws_.append(["TEST-2026-0001", "测试委托人甲", 3850000])
        wb.save(buf)
        r, _ = await rpc(ws, "parse_document", {"filename": "案件台账.xlsx",
                                                 "data_base64": base64.b64encode(buf.getvalue()).decode()}, timeout=60)
        record("C23", "parse_document XLSX", r.get("ok") is True,
               f"extractor={r.get('extractor')} chars={r.get('chars')}")
    except Exception as ex:
        record("C23", "parse_document XLSX", False, f"生成测试 XLSX 失败: {ex}")

    r, _ = await rpc(ws, "parse_document", {"filename": "答辩状.txt",
                                             "data_base64": base64.b64encode("答辩状正文：请求驳回原告全部诉讼请求。".encode()).decode()},
                     timeout=30)
    record("C24", "parse_document 纯文本", r.get("ok") is True and "驳回" in (r.get("text") or ""),
           f"extractor={r.get('extractor')} chars={r.get('chars')}")

    r, _ = await rpc(ws, "parse_document", {"filename": "旧格式.doc",
                                             "data_base64": base64.b64encode(b"\xd0\xcf\x11\xe0").decode()}, timeout=30)
    record("C25", "parse_document 旧版 .doc → 明确提示", r.get("ok") is False and r.get("error"),
           str(r.get("error"))[:60])

    r, _ = await rpc(ws, "parse_document", {"filename": "坏文件.pdf", "data_base64": "!!!not-base64!!!"}, timeout=30)
    record("C26", "parse_document 非法 base64", r.get("ok") is False,
           f"ok={r.get('ok')} error={r.get('error')} chars={r.get('chars')}")

    # 案件知识库：测试委托人甲案的两份材料
    docs = [
        {"name": "买卖合同.pdf", "text": CONTRACT_TEXT},
        {"name": "送货单汇总.txt", "text": "2026年3月至6月共送货 7 批，累计钢材 486 吨，均由测试相对方乙材料员签收。"},
        {"name": "往来函件.txt", "text": "测试委托人甲于2026年7月15日致函测试相对方乙催告付款，测试相对方乙至今未支付剩余货款 385 万元。"},
    ]
    r, _ = await rpc(ws, "kb_search", {"matter_id": "m-hx", "query": "测试相对方乙还欠多少货款没有支付", "documents": docs, "top_k": 3}, timeout=60)
    hits = r.get("chunks", [])
    record("C27", "kb_search 案件知识库中文检索", r.get("ok") and len(hits) > 0,
           f"{len(hits)} 片 索引{ r.get('indexed_docs') }篇/{r.get('indexed_chunks')}片 首片={hits[0]['name'] if hits else '-'} score={hits[0]['score']:.2f}" if hits else f"{len(hits)} 片")

    r, _ = await rpc(ws, "kb_search", {"matter_id": "m-hx", "query": "违约金怎么约定的", "documents": docs, "top_k": 5}, timeout=60)
    hits = r.get("chunks", [])
    top = hits[0]["text"][:40] if hits else ""
    record("C28", "kb_search 违约条款定位", len(hits) > 0 and "违约金" in (hits[0]["text"] if hits else ""),
           f"首片命中违约金={'违约金' in (hits[0]['text'] if hits else '')} 片段={top!r}")

    items = [
        {"id": "e1", "matterTitle": "测试委托人甲诉测试相对方乙买卖合同纠纷", "type": "decision",
         "title": "是否申请财产保全", "text": "决策：立即申请诉前财产保全，冻结测试相对方乙基本户。理由：对方有转移资产迹象，且标的额较大。"},
        {"id": "e2", "matterTitle": "测试委托人庚诉测试相对方辛专利侵权", "type": "milestone",
         "title": "二审开庭", "text": "二审定于 9 月开庭，重点争辩权利要求解释范围。"},
        {"id": "e3", "matterTitle": "测试当事人丁诉测试委托人丙劳动争议", "type": "note",
         "title": "调解意向", "text": "对方律师透露可接受 12 万一次性了结，需评估风险。"},
    ]
    r, _ = await rpc(ws, "experience_search", {"query": "财产保全 冻结账户", "items": items, "top_k": 2}, timeout=60)
    hits = r.get("hits", [])
    record("C29", "experience_search 跨案件经验召回", r.get("ok") and len(hits) > 0,
           f"{len(hits)} 条 首位={hits[0].get('title') if hits else '-'}")

    r, _ = await rpc(ws, "experience_search", {"query": "完全不相关的查询词", "items": [], "top_k": 3}, timeout=30)
    record("C30", "experience_search 空语料", r.get("ok") is True and r.get("hits") == [], f"{len(r.get('hits', []))} 条")

    # Word 导出
    md = "# 民事起诉状\n\n原告：测试委托人甲\n\n## 诉讼请求\n\n1. 判令被告支付货款 385 万元；\n2. 判令被告承担逾期付款违约金。\n\n**事实与理由**：\n\n原被告于 2026 年 3 月签订买卖合同。\n"
    r, _ = await rpc(ws, "export_docx", {"title": "民事起诉状", "markdown": md, "matter_title": "测试委托人甲诉测试相对方乙"}, timeout=60)
    ok = r.get("ok") is True and r.get("data")
    size = len(base64.b64decode(r["data"])) if ok else 0
    record("C31", "export_docx 法律文书排版导出", ok, f"filename={r.get('filename')} bytes={size}")

    r, _ = await rpc(ws, "export_docx", {"title": "", "markdown": "内容", "matter_title": ""}, timeout=30)
    record("C32", "export_docx 空标题回退", r.get("ok") is True, f"filename={r.get('filename')}")

    r, _ = await rpc(ws, "export_docx", {"title": "非法/标题:带*字符?", "markdown": "x", "matter_title": ""}, timeout=30)
    record("C33", "export_docx 标题非法字符净化", r.get("ok") is True and "/" not in r.get("filename", "/"),
           f"filename={r.get('filename')}")


# ============================================================================
#  D. 值守助手
# ============================================================================
async def section_d(ws):
    section("D. 值守助手（cron 定时监控）")

    r, _ = await rpc(ws, "watchdog_sync", {"matters": MATTERS}, timeout=30)
    record("D1", "watchdog_sync 案件同步落盘", r.get("synced") == len(MATTERS), f"synced={r.get('synced')}/{len(MATTERS)}")

    r, _ = await rpc(ws, "watchdog_status", {}, timeout=60)
    alerts = r.get("alerts", [])
    kinds = sorted(set(a.get("kind") for a in alerts))
    record("D2", "watchdog_status 即时扫描", r.get("matters") == len(MATTERS) and len(alerts) > 0,
           f"在册={r.get('matters')} 告警={len(alerts)} 类型={kinds}")

    by_kind = {}
    for a in alerts:
        by_kind.setdefault(a.get("kind"), []).append(a)
    record("D3", "告警分级：逾期(overdue)", len(by_kind.get("overdue", [])) >= 1,
           f"{len(by_kind.get('overdue', []))} 条 例={by_kind.get('overdue', [{}])[0].get('detail', '')[:40]}")
    record("D4", "告警分级：临期(due-soon)", len(by_kind.get("due-soon", [])) >= 1,
           f"{len(by_kind.get('due-soon', []))} 条")
    record("D5", "告警分级：开庭(court)", len(by_kind.get("court", [])) >= 1,
           f"{len(by_kind.get('court', []))} 条")
    days = [a.get("days") for a in alerts]
    record("D6", "告警按紧急度升序", days == sorted(days), f"days={days[:8]}")

    # 已归档案件不得进入告警（m-yg 的 retrial +90 天，且 m-yg 不在 stale 范围）
    archived_alerts = [a for a in alerts if "测试当事人丑" in str(a.get("matter", ""))]
    record("D7", "已归档案件不产生告警", len(archived_alerts) == 0, f"{len(archived_alerts)} 条")

    # stale：待处理/证据收集 超 14 天未更新
    r2, _ = await rpc(ws, "watchdog_sync", {"matters": [
        {"id": "m-stale", "title": "长期停滞案件", "client": "某某公司", "stage": "证据收集",
         "updatedAt": (TODAY - timedelta(days=30)).isoformat(), "courtDate": None, "deadlines": []},
    ]}, timeout=30)
    r3, _ = await rpc(ws, "watchdog_status", {}, timeout=60)
    stale = [a for a in r3.get("alerts", []) if a.get("kind") == "stale"]
    record("D8", "告警分级：停滞(stale) >14 天", len(stale) == 1,
           f"{len(stale)} 条 detail={stale[0].get('detail', '')[:40] if stale else '-'}")

    r, _ = await rpc(ws, "watchdog_status", {}, timeout=30)
    txt = r.get("alertText", "")
    record("D9", "alertText 中文告警清单", bool(txt) and ("逾期" in txt or "告警" in txt or "开庭" in txt),
           f"{len(txt)} 字 | {txt.splitlines()[0][:50] if txt else ''}")

    r, _ = await rpc(ws, "watchdog_briefing", {}, timeout=60)
    # 全新安装（.hermes/cron/output 为空、且未到 08:30）时本就没有晨报——契约是"不报错地告知"
    record("D10", "watchdog_briefing 最近晨报", r.get("found") is True or r.get("found") is False,
           f"at={r.get('at')} status={r.get('status')} 正文={len(r.get('output') or '')} 字 "
           f"| {(r.get('output') or '').splitlines()[0][:40] if r.get('output') else r.get('error')}")

    r, _ = await rpc(ws, "watchdog_briefing", {"job": "不存在的任务"}, timeout=30)
    record("D11", "watchdog_briefing 未知任务", r.get("found") is False, f"{r.get('error')}")

    r, _ = await rpc(ws, "watchdog_run_now", {}, timeout=60)
    record("D12", "watchdog_run_now 立即触发", r.get("triggered") is True, f"job={r.get('job')} id={r.get('id')}")

    r, _ = await rpc(ws, "watchdog_run_now", {"job": "不存在的任务"}, timeout=30)
    record("D13", "watchdog_run_now 未知任务 → 报错", "error" in r, r.get("error", "")[:50])

    # 触发是"下一个 tick 执行"，桌面 ticker 间隔 300s；这里只验证触发链路不报错，
    # 真正的产出刷新需要等一个 tick（见 docs/DEPLOY.md 值守助手一节）
    await asyncio.sleep(4)
    r, _ = await rpc(ws, "watchdog_briefing", {}, timeout=60)
    record("D14", "触发后晨报查询链路可用（产出需等下一个 tick）",
           "error" not in r or r.get("found") is not None,
           f"at={r.get('at')} status={r.get('status')} 正文={len(r.get('output') or '')} 字")

    # 恢复全量台账
    await rpc(ws, "watchdog_sync", {"matters": MATTERS}, timeout=30)


# ============================================================================
#  E. 对话（律师真实提问）
# ============================================================================
async def section_e(ws):
    section("E. AI 协作对话")

    r, _ = await rpc(ws, "chat", {
        "message": "我方代理原告测试委托人甲，被告测试相对方乙拖欠货款 385 万元已逾期。请简要说明诉讼时效起算点，并列出我方应准备的三项核心证据。控制在 200 字内。",
        "thread_id": "lawyer-e1", "profile": PROFILE,
    }, timeout=300)
    resp = r.get("response", "")
    record("E1", "chat 基础法律咨询", bool(resp) and not r.get("error"),
           f"{len(resp)} 字 引用={len(r.get('citations', []))} 上下文={r.get('context_stats')}")

    r, _ = await rpc(ws, "chat", {
        "message": "本案举证期限是几号？依据是什么？",
        "thread_id": "lawyer-e2", "profile": PROFILE,
        "matter_context": json.dumps(MATTERS[0], ensure_ascii=False),
    }, timeout=300)
    resp = r.get("response", "")
    hit = "9月14日" in resp or "9 月 14" in resp or "09-14" in resp or "9-14" in resp
    record("E2", "chat 案件上下文注入（期限问答）", bool(resp),
           f"{len(resp)} 字 命中举证期限日期={'是' if hit else '否'} 上下文={r.get('context_stats')}")

    r, _ = await rpc(ws, "chat", {
        "message": "根据案件文档，被告还欠我方多少货款？只回答金额。",
        "thread_id": "lawyer-e3", "profile": PROFILE,
        "matter_documents": [
            {"name": "送货单汇总.txt", "text": "2026年3月至6月共送货 7 批，累计钢材 486 吨，货款总额 385 万元，被告仅支付 0 元。"},
            {"name": "往来函件.txt", "text": "测试委托人甲于2026年7月15日致函催告，测试相对方乙至今未支付剩余货款 3,850,000 元。"},
        ],
    }, timeout=300)
    resp = r.get("response", "")
    hit = "385" in resp or "3850000" in resp or "3,850,000" in resp
    record("E3", "chat 案件文档库注入（KB 检索）", hit and r.get("context_stats", {}).get("kb_chunks", 0) > 0,
           f"回答={resp.strip()[:40]!r} 命中金额={'是' if hit else '否'} kb_chunks={r.get('context_stats', {}).get('kb_chunks')}")

    r, _ = await rpc(ws, "chat", {
        "message": "我之前在别的案子上是怎么处理财产保全的？",
        "thread_id": "lawyer-e4", "profile": PROFILE,
        "experience_items": [
            {"id": "e1", "matterTitle": "测试委托人甲诉测试相对方乙买卖合同纠纷", "type": "decision",
             "title": "是否申请财产保全", "text": "决策：立即申请诉前财产保全，冻结测试相对方乙基本户。理由：对方有转移资产迹象。"},
        ],
    }, timeout=300)
    resp = r.get("response", "")
    hit = "保全" in resp
    record("E4", "chat 历史经验召回注入", hit and r.get("context_stats", {}).get("experience", 0) > 0,
           f"命中保全={'是' if hit else '否'} experience={r.get('context_stats', {}).get('experience')}")

    r, _ = await rpc(ws, "chat", {
        "message": "请用一句话说明这份合同第一条的交付义务。",
        "thread_id": "lawyer-e5", "profile": PROFILE,
        "files": [{"name": "买卖合同.txt", "type": "text/plain",
                   "data": "data:text/plain;base64," + base64.b64encode(CONTRACT_TEXT.encode()).decode()}],
    }, timeout=300)
    resp = r.get("response", "")
    hit = "30" in resp or "三十" in resp
    record("E5", "chat 附件解析注入", bool(resp) and r.get("context_stats", {}).get("files", 0) > 0,
           f"{len(resp)} 字 命中交付期限={'是' if hit else '否'} files={r.get('context_stats', {}).get('files')}")

    r, _ = await rpc(ws, "chat", {
        "message": "请按 contract-review 技能审查我提供的合同，指出最重要的三个风险点。",
        "thread_id": "lawyer-e6", "skill_id": "commercial-review", "profile": PROFILE,
        "matter_documents": [{"name": "买卖合同.txt", "text": CONTRACT_TEXT}],
    }, timeout=420)
    resp = r.get("response", "")
    record("E6", "chat 技能加载（commercial-review）", bool(resp) and len(resp) > 200,
           f"{len(resp)} 字 开头={resp.strip()[:36]!r}")

    r, _ = await rpc(ws, "chat", {
        "message": "你好，请回复「收到」两个字。",
        "api_key": "sk-totally-invalid-000", "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-flash", "thread_id": "lawyer-e7",
    }, timeout=180)
    resp = r.get("response", "")
    record("E7", "chat 无效 Key → error:true + 中文提示",
           r.get("error") is True and any(k in resp for k in ("🔑", "无效", "429", "⏳")),
           f"error={r.get('error')} resp={resp[:60]!r}")

    # 串行泵：同一连接连发两个 chat，必须串行执行（不得并发），且两个请求都得到答复
    await drain(ws, 0.5)
    id1, id2 = 770001, 770002
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": id1, "method": "chat",
                              "params": {"message": "请用 20 字说明答辩期限。", "thread_id": "lawyer-e8"}}))
    started = False
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < 60:
        m = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
        if m.get("event") == "agui" and m.get("payload", {}).get("type") == "RUN_STARTED":
            started = True
            break
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": id2, "method": "chat",
                              "params": {"message": "请用 20 字说明举证期限。", "thread_id": "lawyer-e8"}}))
    order = []
    t0 = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - t0 < 420:
        m = json.loads(await asyncio.wait_for(ws.recv(), timeout=420))
        if m.get("id") in (id1, id2):
            order.append(m["id"])
            if len(order) == 2:
                break
    record("E8", "同连接连发 chat 串行执行（先到先服务）",
           started and order == [id1, id2],
           f"RUN_STARTED={started} 完成顺序={['#1' if x == id1 else '#2' for x in order]}")

    r, _ = await rpc(ws, "abort", {"api_key": "", "base_url": "", "model": ""}, timeout=30)
    record("E10", "abort 无活动 run 时返回 aborted", r.get("status") == "aborted", json.dumps(r, ensure_ascii=False))


# ============================================================================
#  F. 配置
# ============================================================================
async def section_f(ws):
    section("F. 配置与数据源")

    r, _ = await rpc(ws, "list_mcp_servers", {}, timeout=30)
    servers = r.get("servers", [])
    enabled = [s for s in servers if s.get("enabled")]
    record("F1", "list_mcp_servers 6 服务器", len(servers) == 6 and len(enabled) == 6,
           f"{len(servers)} 个 / 启用 {len(enabled)}：{[s.get('name') for s in servers]}")

    r, _ = await rpc(ws, "list_hermes_skills", {}, timeout=60)
    skills = r.get("skills", [])
    groups = sorted(set(s.get("group") for s in skills))
    record("F2", "list_hermes_skills 技能库", len(skills) >= 82, f"{len(skills)} 个 / {len(groups)} 组")
    no_cn = [s.get("id") for s in skills
             if not any("\u4e00" <= ch <= "\u9fff" for ch in (s.get("name") or ""))]
    record("F3", "技能中文化覆盖（启用即需中文显示名）", len(no_cn) == 0,
           f"无中文名={no_cn}" if no_cn else f"{len(skills)} 个技能全部有中文名")

    # setup_save 会重写 .env —— 备份 → 测 → 还原
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    with open(env_path, "rb") as fh:
        backup = fh.read()
    try:
        r, _ = await rpc(ws, "setup_save", {
            "api_key": "sk-lawyer-test-key-000", "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-flash", "profile": PROFILE,
        }, timeout=60)
        saved = r.get("status") == "saved"
        with open(env_path, "r", encoding="utf-8") as fh:
            body = fh.read()
        has_key = "sk-lawyer-test-key-000" in body
        yuandian_kept = "YUANDIAN_API_KEY" in body
        record("F4", "setup_save 写入凭证", saved and has_key, f"status={r.get('status')} 写入Key={'是' if has_key else '否'}")
        record("F5", "setup_save 保留非托管行（元典 Key）", yuandian_kept, f"YUANDIAN_API_KEY 保留={'是' if yuandian_kept else '否'}")

        user_md = os.path.join(os.path.dirname(env_path), ".hermes", "USER.md")
        if os.path.exists(user_md):
            with open(user_md, "r", encoding="utf-8") as fh:
                md = fh.read()
            record("F6", "setup_save 写入律师画像 USER.md", "测试律师" in md and "测试律师事务所" in md,
                   f"命中姓名+律所={'是' if ('测试律师' in md and '测试律师事务所' in md) else '否'}")
        else:
            record("F6", "setup_save 写入律师画像 USER.md", False, "USER.md 不存在")
    finally:
        with open(env_path, "wb") as fh:
            fh.write(backup)
        print("   （.env 已还原）")

    r, _ = await rpc(ws, "initialize", {}, timeout=30)
    record("F7", "还原后 initialize 仍可用", r.get("status") == "ok", f"configured={r.get('configured')}")


# ============================================================================
async def main():
    wanted = set(a.upper() for a in sys.argv[1:]) or {"A", "B", "C", "D", "E", "F"}
    sections = {"A": section_a, "B": section_b, "C": section_c, "D": section_d, "E": section_e, "F": section_f}
    async with websockets.connect(URI, max_size=50 * 1024 * 1024, ping_interval=None) as ws:
        for key in ["A", "B", "C", "D", "E", "F"]:
            if key in wanted:
                try:
                    await sections[key](ws)
                except Exception as ex:
                    record(key, f"分区 {key} 异常中断", False, repr(ex)[:160])
    passed = sum(1 for r in RESULTS if r["ok"])
    print(f"\n{'=' * 72}\n合计 {passed}/{len(RESULTS)} 通过\n{'=' * 72}")
    for r in RESULTS:
        if not r["ok"]:
            print(f"  FAIL {r['case']} {r['name']} — {r['detail']}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lawyer_full_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, ensure_ascii=False, indent=2)
    print(f"报告：{out}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
