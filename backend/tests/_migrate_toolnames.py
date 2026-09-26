"""元典工具名迁移：旧的 rh_* 名称 → 2026-09 服务端改版后的英文名。

覆盖两处遗漏（上一轮只替换了蛇形名，漏了驼峰式）：
  - prc-legal-research-company-search：23 个 yuandian_rh_enterprise* 驼峰名
  - civil-cargo-damage-claim：yuandian_case_vector_search / yuandian_rh_ft_detail

映射依据 `tests/_tool_inventory.json` 的真实注册名（65 个 MCP 工具）。
语义对照：失信被执行人(judgment_defaulter) ≠ 被执行人(judicial_enforcement)，不可互换。

用法：runtime/Scripts/python.exe tests/_migrate_toolnames.py [--dry]
"""
import sys
from pathlib import Path

BE = Path(r"D:\LawClaw\backend")
SK = BE / ".hermes" / "skills"
DRY = "--dry" in sys.argv

MAP = {
    "yuandian_rh_enterpriseSearch": "yuandian_search_companies",
    "yuandian_rh_enterpriseBaseInfo": "yuandian_get_company_basic_profile",
    "yuandian_rh_enterpriseAggregationSummary": "yuandian_get_company_statistics_overview",
    "yuandian_rh_enterpriseWritAgg": "yuandian_get_company_litigation_statistics",
    "yuandian_rh_enterpriseWritList": "yuandian_list_company_litigation_document_summaries",
    "yuandian_rh_enterpriseCourtSessionNotice": "yuandian_list_company_court_hearing_notices",
    "yuandian_rh_enterpriseCourtNotice": "yuandian_list_company_court_announcements",
    "yuandian_rh_enterpriseExecutions": "yuandian_list_company_judgment_defaulter_records",
    "yuandian_rh_enterpriseExecutedPerson": "yuandian_list_company_judicial_enforcement_records",
    "yuandian_rh_enterpriseSeriousIllegal": "yuandian_list_company_serious_violations",
    "yuandian_rh_enterpriseAbnormalOperation": "yuandian_list_company_abnormal_operations",
    "yuandian_rh_enterpriseCorporateTax": "yuandian_list_company_tax_arrears",
    "yuandian_rh_enterprisePunishment": "yuandian_list_company_administrative_penalties",
    "yuandian_rh_enterpriseFrozenEquity": "yuandian_list_company_equity_freezes",
    "yuandian_rh_enterprisePledge": "yuandian_list_company_equity_pledges",
    "yuandian_rh_enterpriseOutInvest": "yuandian_list_company_external_investments",
    "yuandian_rh_enterpriseGuaranty": "yuandian_list_company_external_guarantees",
    "yuandian_rh_enterpriseBrand": "yuandian_list_company_trademarks",
    "yuandian_rh_enterprisePatent": "yuandian_list_company_patents",
    "yuandian_rh_enterpriseSoftRight": "yuandian_list_company_software_copyrights",
    "yuandian_rh_enterpriseWorksRight": "yuandian_list_company_work_copyrights",
    "yuandian_rh_enterpriseIcp": "yuandian_list_company_website_filings",
    "yuandian_rh_enterpriseChangeInfo": "yuandian_list_company_registration_changes",
    "yuandian_case_vector_search": "yuandian_semantic_search_cases",
    "yuandian_law_vector_search": "yuandian_semantic_search_legal_articles",
    "yuandian_rh_ft_detail": "yuandian_get_legal_article_detail",
}

order = sorted(MAP, key=len, reverse=True)
total = {}
changed = []
for p in sorted(SK.rglob("*.md")):
    src = p.read_text(encoding="utf-8", errors="replace")
    out = src
    for old in order:
        if old in out:
            total[old] = total.get(old, 0) + src.count(old)
            out = out.replace(old, MAP[old])
    if out != src:
        changed.append(str(p.relative_to(SK)).replace("\\", "/"))
        if not DRY:
            p.write_text(out, encoding="utf-8", newline="\n")

print(("【dry-run】" if DRY else "") + f"改动文件数: {len(changed)}")
for f in changed:
    print("   " + f)
print(f"替换总数: {sum(total.values())}")
for k, v in sorted(total.items(), key=lambda kv: -kv[1]):
    print(f"  {v:3d}  {k} -> {MAP[k]}")
