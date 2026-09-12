"""
LawClaw 法规检索工具
主要数据源：元典开放平台 (open.chineselaw.com) — 免费注册，提供法规/法条搜索
付费升级路径：北大法宝 MCP / 元典高级 API
回退方案：内置常用法规 JSON 索引
"""
import json
import os
import requests
from tools.registry import registry


def check_requirements() -> bool:
    return bool(os.environ.get("YD_OPEN_API_KEY") or os.environ.get("YUANDIAN_API_KEY"))


def legal_search(query: str, search_type: str = "law", max_results: int = 10, task_id: str = None) -> str:
    """检索中国法律法规"""
    api_key = os.environ.get("YD_OPEN_API_KEY") or os.environ.get("YUANDIAN_API_KEY")
    if not api_key:
        return json.dumps({
            "results": [],
            "total": 0,
            "note": "需要配置 YUANDIAN_API_KEY 或 YD_OPEN_API_KEY 环境变量。注册地址：https://open.chineselaw.com/"
        }, ensure_ascii=False)

    try:
        payload = {"keyword": query, "pageNo": 1, "pageSize": max_results}
        resp = requests.post(
            "https://open.chineselaw.com/open/rh_fg_search",
            json=payload,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=15,
        )
        data = resp.json()
        items = []
        if isinstance(data.get("data"), dict):
            items = data["data"].get("list", [])
        elif isinstance(data.get("data"), list):
            items = data["data"]

        results = []
        for item in items:
            results.append({
                "title": item.get("fgmc", ""),
                "publish_date": item.get("fbrq", ""),
                "department": item.get("jgmc", ""),
                "doc_id": item.get("id", ""),
                "source": "元典开放平台",
                "effective": item.get("sxx", "有效") == "有效",
            })
        return json.dumps({"results": results, "total": len(results)}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"results": [], "total": 0, "error": str(e)}, ensure_ascii=False)


registry.register(
    name="legal_search",
    toolset="legal",
    schema={
        "name": "legal_search",
        "description": "检索中国法律法规，支持按关键词查询。数据源：元典开放平台（需配置 API Key）。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如'民法典'、'公司法'"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["law", "case", "judicial_interpretation"],
                    "description": "搜索类型：law=法律法规（默认）, case=判例, judicial_interpretation=司法解释"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回数量",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    handler=lambda args, **kw: legal_search(
        query=args.get("query", ""),
        search_type=args.get("search_type", "law"),
        max_results=args.get("max_results", 10),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=["YD_OPEN_API_KEY", "YUANDIAN_API_KEY"],
)
