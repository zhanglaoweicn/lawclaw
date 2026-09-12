# -*- coding: utf-8 -*-
"""LawClaw 值守助手——基于 Hermes cron 的定时监控层（借鉴 claude-for-legal agents/ 蓝图本地化）。

能力：
- 案件摘要同步：前端把 matters 摘要推给后端落盘（watchdog_sync）
- 扫描告警：逾期期限 / 7日内临期 / 7日内开庭 / 待处理超14天无进展
- 定时晨报：Hermes cron（工作日 08:30）扫描脚本注入数据 → agent 生成执业晨报
- 状态查询：watchdog_status（即时告警 + 最近晨报）；trigger_job 立即生成

基础设施全部复用上游 hardened 组件：cron/scheduler（tick lock、追赶窗口、3 分钟硬中断）、
hermes_cli/web_server._start_desktop_cron_ticker（桌面后端 ticker，跨进程安全）。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / ".hermes" / "data"
MATTERS_SNAPSHOT = DATA_DIR / "watchdog_matters.json"

_MORNING_JOB = "lawclaw-morning-briefing"
_WEEKLY_JOB = "lawclaw-weekly-review"

_start_lock = threading.Lock()
_ticker_started = False


# ── 数据同步 ────────────────────────────────────────────────
def sync_matters(matters: List[Dict[str, Any]]) -> int:
    """前端推送的案件摘要落盘。条目字段：id/title/stage/updatedAt/client/
    deadlines[{type,date,completed}], courtDate。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    slim = []
    for m in matters or []:
        slim.append({
            "id": m.get("id", ""),
            "title": m.get("title", ""),
            "client": m.get("client", ""),
            "stage": m.get("stage", ""),
            "updatedAt": str(m.get("updatedAt", "")),
            "courtDate": m.get("courtDate"),
            "deadlines": [
                {"type": d.get("type"), "date": d.get("date"),
                 "completed": bool(d.get("completed")), "note": d.get("note", "")}
                for d in (m.get("deadlines") or [])
            ],
        })
    MATTERS_SNAPSHOT.write_text(json.dumps({"syncedAt": datetime.now().isoformat(timespec="seconds"),
                                            "matters": slim}, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return len(slim)


def load_synced_matters() -> List[Dict[str, Any]]:
    try:
        return json.loads(MATTERS_SNAPSHOT.read_text(encoding="utf-8")).get("matters", [])
    except Exception:
        return []


# ── 扫描告警（纯函数，cron 脚本与 RPC 共用） ─────────────────
def scan_alerts(matters: List[Dict[str, Any]], now: datetime | None = None) -> List[Dict[str, Any]]:
    now = now or datetime.now()
    alerts: List[Dict[str, Any]] = []
    for m in matters:
        title = m.get("title", "")
        for d in m.get("deadlines") or []:
            if d.get("completed"):
                continue
            try:
                dt = datetime.fromisoformat(str(d["date"]).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            days = (dt.date() - now.date()).days
            if days < 0:
                alerts.append({"kind": "overdue", "matter": title, "detail": f"{d.get('type') or '期限'}已逾期 {-days} 天",
                               "date": dt.strftime("%m-%d"), "days": days})
            elif days <= 7:
                alerts.append({"kind": "due-soon", "matter": title, "detail": f"{d.get('type') or '期限'}还剩 {days} 天",
                               "date": dt.strftime("%m-%d"), "days": days})
        cd = m.get("courtDate")
        if cd:
            try:
                cdt = datetime.fromisoformat(str(cd).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            days = (cdt.date() - now.date()).days
            if 0 <= days <= 7:
                alerts.append({"kind": "court", "matter": title, "detail": f"{days} 天后开庭",
                               "date": cdt.strftime("%m-%d"), "days": days})
        # 僵化案件：待处理/证据收集 超 14 天未更新
        if m.get("stage") in ("待处理", "证据收集"):
            try:
                upd = datetime.fromisoformat(str(m.get("updatedAt", "")).replace("Z", "+00:00")).replace(tzinfo=None)
                if (now - upd).days > 14:
                    alerts.append({"kind": "stale", "matter": title,
                                   "detail": f"处于「{m.get('stage')}」已 {(now - upd).days} 天无进展",
                                   "date": upd.strftime("%m-%d"), "days": (now - upd).days})
            except Exception:
                pass
    alerts.sort(key=lambda a: a["days"])
    return alerts


def alerts_to_text(alerts: List[Dict[str, Any]]) -> str:
    if not alerts:
        return "扫描完成：当前无逾期期限、临期事项、近期开庭或停滞案件。"
    lines = [f"共 {len(alerts)} 项告警："]
    kind_label = {"overdue": "已逾期", "due-soon": "临期", "court": "开庭", "stale": "停滞"}
    for a in alerts:
        lines.append(f"- [{kind_label.get(a['kind'], a['kind'])}] {a['matter']} — {a['detail']}（{a['date']}）")
    return "\n".join(lines)


# ── cron jobs（幂等注册） ───────────────────────────────────
# no_agent=True：script stdout 即交付内容（纯扫描清单，无 LLM 依赖、可靠送达）。
# AI 分析简报由前端「生成 AI 晨报」按钮经普通 chat 链路按需生成。
_SCAN_SCRIPT = str((BACKEND_DIR / ".hermes" / "scripts" / "watchdog_scan.py").resolve())


def ensure_watchdog_jobs(config_enabled: bool = True) -> dict:
    """幂等注册晨报（工作日 08:30）与周报（周日 20:00）。返回 {job名: job_id或状态}。

    no_agent=True：script stdout 即交付（纯扫描清单，无 LLM/凭证依赖——cron 会话的
    provider 凭证解析在 LawClaw 自建后端里不可靠，见调试记录）。AI 分析简报由前端
    「生成 AI 晨报」按钮经普通 chat 链路按需生成。script 变更时删除重建。
    """
    from cron import jobs as cron_jobs
    out = {}
    existing = {j.get("name"): j for j in cron_jobs.list_jobs(include_disabled=True)}
    specs = [
        (_MORNING_JOB, "30 8 * * 1-5", config_enabled),
        (_WEEKLY_JOB, "0 20 * * 0", config_enabled),
    ]
    for name, schedule, enabled in specs:
        old = existing.get(name)
        if old and not enabled:
            out[name] = "disabled-by-config"
            continue
        # script 版本变化 → 删除重建（保证扫描逻辑新鲜）
        if old and old.get("script") != _SCAN_SCRIPT:
            try:
                cron_jobs.remove_job(old["id"])
            except Exception:
                pass
            old = None
        if old:
            out[name] = old.get("id") or "exists"
            continue
        if not enabled:
            out[name] = "disabled-by-config"
            continue
        rec = cron_jobs.create_job(
            prompt=name, schedule=schedule, name=name,
            script=_SCAN_SCRIPT, deliver="local", no_agent=True,
        )
        out[name] = rec.get("id") or "created"
    return out


def get_latest_briefing(job_name: str = _MORNING_JOB) -> Dict[str, Any]:
    """最近一次该 cron job 的执行输出。

    no_agent 任务的 stdout 落盘于 `<home>/cron/output/<job_id>/<时间戳>.md`；
    执行记录（executions）只有状态无正文，故从输出目录读取。
    """
    from cron import jobs as cron_jobs
    try:
        home = Path(os.environ.get("HERMES_HOME") or (BACKEND_DIR / ".hermes"))
        jobs = {j.get("name"): j for j in cron_jobs.list_jobs(include_disabled=True)}
        job = jobs.get(job_name)
        if not job:
            return {"found": False, "error": "值守任务未注册"}
        out_dir = home / "cron" / "output" / str(job.get("id"))
        files = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime) if out_dir.is_dir() else []
        if not files:
            return {"found": False, "error": None}
        latest = files[-1]
        body = latest.read_text(encoding="utf-8", errors="replace")
        # 剥离投递文件头（--- 分隔线之前），只留晨报正文
        if "\n---\n" in body:
            body = body.split("\n---\n", 1)[1].strip()
        status = "completed"
        try:
            recs = ce_list(job.get("id"))
            if recs:
                status = recs[0].get("status") or status
        except Exception:
            pass
        return {"found": True, "output": body[:4000], "status": status,
                "at": datetime.fromtimestamp(latest.stat().st_mtime).isoformat(timespec="seconds")}
    except Exception as e:
        return {"found": False, "error": str(e)[:120]}


def ce_list(job_id: str):
    from cron import executions as cron_exec
    return cron_exec.list_executions(job_id=job_id, limit=1)


# ── ticker 启动 ──────────────────────────────────────────────
def start_ticker(interval: int = 300) -> bool:
    """启动桌面 cron ticker（工作日晨报等 job 依赖它触发）。

    _start_desktop_cron_ticker 为上游桌面后端专用入口（tick lock 跨进程安全）。
    LawClaw 后端与 hermes dashboard 同形态，直接复用。失败不阻塞主流程。
    """
    global _ticker_started
    with _start_lock:
        if _ticker_started:
            return True
        try:
            sync_profile_env()
            os.environ.setdefault("HERMES_DESKTOP", "1")  # 语义：由应用拉起的后端
            from hermes_cli.web_server import _start_desktop_cron_ticker
            stop_event = threading.Event()
            t = threading.Thread(target=_start_desktop_cron_ticker,
                                 args=(stop_event, interval), daemon=True,
                                 name="lawclaw-cron-ticker")
            t.start()
            _ticker_started = True
            return True
        except Exception as e:
            print(f"[watchdog] cron ticker 启动失败（值守晨报不可用）: {e}")
            return False


def get_status() -> Dict[str, Any]:
    """即时扫描 + 同步信息 + 晨报可达性。"""
    matters = load_synced_matters()
    alerts = scan_alerts(matters)
    return {
        "syncedAt": (MATTERS_SNAPSHOT.exists() and datetime.fromtimestamp(
            MATTERS_SNAPSHOT.stat().st_mtime).isoformat(timespec="seconds")) or None,
        "matters": len(matters),
        "alerts": alerts,
        "alertText": alerts_to_text(alerts),
    }

def sync_profile_env() -> bool:
    """把 backend/.env 同步到 backend/.hermes/.env。

    cron 会话执行时以 profile secret scope（<home>/.env）解析 LLM 凭证；
    LawClaw 的 .env 在 backend/ 根，不同步则 cron 会话拿到空 key（401 no-key-required）。
    """
    src = BACKEND_DIR / ".env"
    dst = BACKEND_DIR / ".hermes" / ".env"
    try:
        if src.exists():
            shutil.copy2(src, dst)
            return True
    except Exception as e:
        print(f"[watchdog] profile .env 同步失败: {e}")
    return False
