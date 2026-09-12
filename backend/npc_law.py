# -*- coding: utf-8 -*-
"""国家法律法规数据库（flk.npc.gov.cn）二期 API 客户端。

2025-08-20 二期升级后的官方接口（无认证、无验证码）：
- 法规搜索：POST /law-search/search/list（标题/正文、精确/模糊、时效性过滤）
- 时效性官方字段：sxx 3=有效 / 2=已修改 / 1=已废止 / 4=未生效
- 限流对策：连续请求约 20 次后返回空响应 → 请求间隔 0.5s + 1s/2s/4s 递增重试
- TTL 缓存：法规时效性变化极低频，同一法规名 24h 内直接复用

端点与参数基于公开网络流量整理（参考 community 文档，2026-05 实测口径）；
本模块为自研实现，未复制任何第三方代码。

用法：
    from npc_law import search_law
    rows = search_law("民法典")   # [{title, bbbs, sxx, gbrq, sxrq, flxz}, ...]
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Dict, List, Optional

import requests

BASE = "https://flk.npc.gov.cn"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_HEADERS = {"Content-Type": "application/json;charset=utf-8", "User-Agent": _UA}

# sxx 数字 → 中文状态（官方口径）
SXX_MAP = {1: "已废止", 2: "已修改", 3: "现行有效", 4: "未生效"}
SXX_TEXT_MAP = {"现行有效": 3, "有效": 3, "已修改": 2, "已修正": 2, "已废止": 1, "失效": 1, "已失效": 1, "未生效": 4}

_REQUEST_INTERVAL = 0.5          # 官方限流：连续请求约 20 次后空响应
_last_request_ts = 0.0
_rate_lock = threading.Lock()

_CACHE_TTL = 24 * 3600.0
_cache: Dict[str, tuple] = {}    # norm_keyword -> (ts, rows)
_cache_lock = threading.Lock()


def _throttle() -> None:
    """串行化请求并保持 ≥0.5s 间隔（官方限流对策）。"""
    global _last_request_ts
    with _rate_lock:
        wait = _REQUEST_INTERVAL - (time.time() - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        _last_request_ts = time.time()


def _strip_highlight(title: str) -> str:
    """搜索结果标题带 <em class='highlight'> 高亮标签，清洗之。"""
    return re.sub(r"</?em[^>]*>", "", title or "").strip()


def _norm(name: str) -> str:
    """法规名规范化：去书名号/括号/空白/国名前缀，便于贴近匹配。"""
    return re.sub(r"[《》〈〉（）()\s]|中华人民共和国", "", name or "")


def search_law(keyword: str, page_size: int = 20, use_cache: bool = True) -> List[Dict[str, Any]]:
    """按标题模糊搜索法规。返回规范化行：title（无高亮标签）、bbbs、sxx(int)、gbrq、sxrq、flxz。

    用高级检索端点（title 字段条件）而非基础 search/list——后者的分词相关度排序
    不可控（实测搜"合同法"返回大量无关法律）；高级检索 title 条件召回精准
    （"合同法" total=5 且前几条即目标法规本体）。
    """
    key = _norm(keyword)
    if not key:
        return []
    if use_cache:
        with _cache_lock:
            hit = _cache.get(key)
            if hit and time.time() - hit[0] < _CACHE_TTL:
                return hit[1]

    body = {
        "dataList": [{"fieldName": "title", "values": [keyword], "searchType": 2, "link": 0, "index": 0}],
        "orderByParam": {"order": "", "sort": ""},
        "pageNum": 1,
        "pageSize": min(page_size, 50),   # 高级检索 pageSize 上限 50
    }
    rows: List[Dict[str, Any]] = []
    last_err: Optional[str] = None
    for attempt in range(4):     # 1 次正常 + 3 次递增重试（1s/2s/4s）
        _throttle()
        try:
            resp = requests.post(f"{BASE}/law-search/highSearch/highSearch",
                                 data=json.dumps(body), headers=_HEADERS, timeout=20)
            data = resp.json()
            # 官方限流时可能返回空响应体：视为本次失败进入重试
            if not isinstance(data, dict) or not data:
                last_err = "empty response"
                time.sleep(2 ** attempt)
                continue
            raw_rows = data.get("rows") or []
            rows = [{
                "title": _strip_highlight(it.get("title")),
                "bbbs": it.get("bbbs", ""),
                "sxx": _sxx_to_int(it.get("sxx")),
                "gbrq": it.get("gbrq") or "",
                "sxrq": it.get("sxrq") or "",
                "flxz": it.get("flxz") or "",
            } for it in raw_rows]
            last_err = None
            break
        except Exception as e:   # 网络抖动/读超时 → 递增重试（实测偶发 15s 读超时）
            last_err = str(e)
            time.sleep(2 ** attempt)
    if last_err and not rows:
        raise RuntimeError(f"flk.npc.gov.cn 搜索失败: {last_err}")
    with _cache_lock:
        _cache[key] = (time.time(), rows)
    return rows


def _sxx_to_int(v: Any) -> int:
    """sxx 可能是数字或中文，统一映射为 1/2/3/4；未知返回 0。"""
    if v in (1, 2, 3, 4):
        return int(v)
    if isinstance(v, str):
        if v.strip().isdigit():
            return int(v.strip())
        return SXX_TEXT_MAP.get(v.strip(), 0)
    return 0


def find_law_status(law_name: str) -> Optional[Dict[str, Any]]:
    """在搜索结果中定位与 law_name 最贴近的法规行（规范化后包含匹配，取标题最短者）。

    返回 {title, sxx, status, gbrq, sxrq, bbbs} 或 None（未找到）。
    """
    law_norm = _norm(law_name)
    if not law_norm:
        return None
    rows = search_law(law_name)
    candidates = [r for r in rows
                  if (_t := _norm(r["title"])) and (law_norm in _t or _t in law_norm)]
    if not candidates:
        return None
    best = min(candidates, key=lambda r: len(_norm(r["title"])))
    return {
        "title": best["title"],
        "sxx": best["sxx"],
        "status": SXX_MAP.get(best["sxx"], "未知"),
        "gbrq": best["gbrq"],
        "sxrq": best["sxrq"],
        "bbbs": best["bbbs"],
    }

def get_docx_url(bbbs: str, fmt: str = "docx") -> str:
    """获取官方法规文件下载签名 URL（两步：PC 端点返回 AWS 风格签名地址，约 1 小时有效）。

    前端拿到 URL 直接 window.open 即可下载官方 DOCX/PDF。
    """
    _throttle()
    resp = requests.get(f"{BASE}/law-search/download/pc",
                        params={"format": fmt, "bbbs": bbbs, "fileId": ""},
                        headers={"User-Agent": _UA}, timeout=20)
    data = resp.json()
    url = (data.get("data") or {}).get("url") if isinstance(data.get("data"), dict) else None
    if not url:
        raise RuntimeError(f"获取下载地址失败: {data.get('msg') or data.get('message') or '无 url 字段'}")
    return url
