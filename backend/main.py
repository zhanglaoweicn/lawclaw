import sys
import io
import json
import os
import re
import threading
import asyncio
import traceback
from pathlib import Path

# 冻结模式（PyInstaller）：__file__ 在临时解包目录，改用 exe 所在目录定位运行时文件
# （发行形态 = backend/ 内含 lawclaw-backend.exe + _internal/ + config.yaml + .env + .hermes/）
if getattr(sys, "frozen", False):
    BACKEND_DIR = Path(sys.executable).resolve().parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    BACKEND_DIR = Path(__file__).parent
    PROJECT_ROOT = BACKEND_DIR.parent
    sys.path.insert(0, str(PROJECT_ROOT))

# Isolate Hermes state to backend/.hermes/ — separate from user's ~/.hermes/
os.environ.setdefault("HERMES_HOME", str(BACKEND_DIR / ".hermes"))
# Legal Agent profile & data paths (required by 元力工场 skill packs)
os.environ.setdefault("LEGAL_AGENT_PROFILE_HOME", str(BACKEND_DIR / ".hermes" / "profiles"))
os.environ.setdefault("LEGAL_AGENT_LOCAL_DATA_HOME", str(BACKEND_DIR / ".hermes" / "data"))

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

from run_agent import AIAgent
from tools.mcp_tool_discovery import discover_mcp_tools  # 上游 2026-09 重构：MCP 发现独立模块
import doc_intel  # 文档抽取适配层 + 案件知识库 + 经验记忆（BM25）
from citations import DEPRECATED_LAWS, extract_citations, num_to_cn as _num_to_cn  # 法条引用抽取（纯函数模块）
import npc_law  # 国家法律法规数据库（flk.npc.gov.cn）官方时效性主源
import watchdog  # 值守助手（案件扫描告警 + Hermes cron 晨报/周报）

# Discover MCP servers (元典 law/case/company)
# 未配置元典 Key 时整体跳过：空 Authorization 头（"Bearer "）会让 6 个服务器各重试 3 次，
# 拖慢启动 30-40 秒并刷 6 行报错——客户版首启尤其难堪。填入 Key 后自动恢复。
_YD_KEY_PRESENT = bool(
    (os.environ.get("YUANDIAN_API_KEY") or os.environ.get("YD_OPEN_API_KEY") or "").strip()
)
try:
    if _YD_KEY_PRESENT:
        discover_mcp_tools()
    else:
        print("[LawClaw] 未配置元典数据源（YUANDIAN_API_KEY）→ 跳过法律检索 MCP，"
              "法规/案例检索暂不可用；在安装目录 backend/.env 或「配置」中填入后重启即可启用")
except Exception:
    import traceback
    traceback.print_exc()

# ── 值守助手：启动桌面 cron ticker + 幂等注册晨报/周报（失败不阻塞主流程）──
try:
    watchdog.start_ticker(interval=300)
    watchdog.ensure_watchdog_jobs(True)   # config.yaml 可加 watchdog.morning_briefing:false 关闭
except Exception as _wd_err:
    print(f"[watchdog] 初始化失败（不影响其他功能）: {_wd_err}")

DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://apihub.agnes-ai.com/v1")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("LAWCLAW_MODEL", "agnes-2.0-flash")

# ── 律师专属法律系统提示词（支持执业画像动态注入） ──
LAWYER_SYSTEM_PROMPT = """你是 LawClaw 律爪，一位专业的中国法律 AI 助手，服务于独立执业律师。

## 核心职责
1. 提供准确、专业的中国法律分析和建议
2. 引用法条时必须标注完整法律名称和条款号（如「《民法典》第584条」）
3. 区分现行有效法律与已废止法律，必要时提示法律修订情况
4. 对法律风险给出明确的风险等级（高/中/低）和建议

## 专业规范
- 仅适用中国大陆法律体系（不含港澳台）
- 涉及诉讼时效时，主动提醒律师注意时效届满风险
- 涉及合同审查时，关注效力性条款、风险分配、违约责任三大维度
- 涉及证据分析时，关注证据的关联性、合法性、真实性
- 涉及文书起草时，确保格式规范、用语准确、逻辑清晰

## 执业伦理
- 始终维护委托人合法权益
- 提示利益冲突风险
- 严格遵守保密义务
- 明确告知「本分析仅供参考，不构成正式法律意见」

## 工具使用
- 优先使用元典 MCP 工具检索最新法条和案例
- 法条引用前应验证其现行有效性
- 复杂法律问题建议多角度分析
- 对方代理律师策略预判时，基于类案数据分析而非主观臆断

## 输出格式
- 法律分析：结论先行 → 法条依据 → 事实适用 → 风险提示
- 合同审查：风险条款标注（🔴高风险/🟡中风险/🟢低风险）+ 修改建议
- 文书起草：标题 + 当事人信息 + 正文 + 落款日期
- 案例分析：案件事实 → 争议焦点 → 法院说理 → 判决要旨 → 实务启示
"""

def build_lawyer_system_prompt(profile: dict = None, base_prompt: str = None) -> str:
    """根据律师执业画像构建个性化系统提示词。

    profile: 来自前端 setupStore.profile 的律师信息
    base_prompt: 自定义系统提示词（如专家角色）；为空则使用默认 LAWYER_SYSTEM_PROMPT
    """
    prompt = base_prompt or LAWYER_SYSTEM_PROMPT
    if not profile or not isinstance(profile, dict):
        return prompt

    # 构建执业画像注入块
    profile_lines = []
    if profile.get("name"):
        profile_lines.append(f"- 律师姓名：{profile['name']}")
    if profile.get("firm"):
        profile_lines.append(f"- 律所：{profile['firm']}")
    if profile.get("title"):
        profile_lines.append(f"- 职位：{profile['title']}")
    if profile.get("yearsOfPractice") is not None:
        years = profile["yearsOfPractice"]
        if isinstance(years, int) and years > 0:
            profile_lines.append(f"- 执业年限：{years} 年")
            if years <= 3:
                profile_lines.append("- 经验等级：初级律师，请适当补充基础法律概念解释")
            elif years <= 8:
                profile_lines.append("- 经验等级：中级律师，使用标准法律术语，无需基础解释")
            else:
                profile_lines.append("- 经验等级：资深律师，可直接讨论前沿法律观点与裁判倾向")
    if profile.get("practiceAreas"):
        areas = profile["practiceAreas"] if isinstance(profile["practiceAreas"], list) else [profile["practiceAreas"]]
        if areas:
            profile_lines.append(f"- 执业领域：{'、'.join(areas)}")
            profile_lines.append("- 请优先围绕该律师执业领域提供深度专业分析")
    if profile.get("teamSize"):
        ts = profile["teamSize"]
        if ts == "solo":
            profile_lines.append("- 团队规模：个人执业（建议关注效率与时间管理）")
        elif ts == "small":
            profile_lines.append("- 团队规模：2-10 人小团队")
        elif ts == "medium":
            profile_lines.append("- 团队规模：11-50 人中型团队")
        elif ts == "large":
            profile_lines.append("- 团队规模：50 人以上大型律所")

    if profile_lines:
        prompt += f"\n\n## 当前律师画像\n" + "\n".join(profile_lines)
        prompt += "\n\n## 个性化要求\n根据以上画像调整回复的深度、术语层次和分析角度。"

    return prompt


_agent_cache = {}
_agent_lock = threading.Lock()

# ── 真中止机制：每个 agent 实例的 abort 事件 ──
# 通过 _agent_abort_events[cache_key] = threading.Event() 跟踪
_agent_abort_events: dict = {}
_agent_abort_lock = threading.Lock()


def _make_agent(api_key=None, base_url=None, model=None):
    """创建 AIAgent 实例。

    关键决策：
    - skip_context_files=True: 避免注入 ~/.hermes/ 下的 SOUL.md/AGENTS.md
      （LawClaw 自有提示词，不需要 Hermes 默认身份）
    - skip_memory=False: 启用 Memory 系统，让执业画像和案件记忆可跨会话保留
      （Memory 默认从 backend/.hermes/MEMORY.md + USER.md 加载）
    - max_iterations=30: 律师场景需要多次工具调用（如先检索法条再验证有效性）
    """
    # 前端历史版本会预写 "demo-mode" 占位 Key；视为未配置，回退到 .env 默认
    if not api_key or api_key == "demo-mode":
        api_key = DEFAULT_API_KEY
    if not base_url or base_url == "demo-mode":
        base_url = DEFAULT_BASE_URL
    return AIAgent(
        base_url=base_url,
        api_key=api_key,
        model=model or DEFAULT_MODEL,
        max_iterations=30,
        quiet_mode=True,
        save_trajectories=False,
        skip_context_files=True,
        skip_memory=False,  # 启用 Memory 系统
    )


def get_agent(api_key=None, base_url=None, model=None):
    key = f"{api_key}:{base_url}:{model}"
    if key not in _agent_cache:
        with _agent_lock:
            if key not in _agent_cache:
                _agent_cache[key] = _make_agent(api_key, base_url, model)
                with _agent_abort_lock:
                    _agent_abort_events[key] = threading.Event()
    return _agent_cache[key]


def get_abort_event(api_key=None, base_url=None, model=None) -> threading.Event:
    """获取与 agent 实例绑定的中止事件。"""
    key = f"{api_key}:{base_url}:{model}"
    with _agent_abort_lock:
        if key not in _agent_abort_events:
            _agent_abort_events[key] = threading.Event()
        return _agent_abort_events[key]


def request_abort(api_key=None, base_url=None, model=None):
    """请求中止当前 agent 的运行。

    通过 Hermes 的 interrupt 机制 + 自定义 abort 事件双重触发：
    1. tools.interrupt.set_interrupt() — 让 agent 的下一轮工具调用检查中断
    2. abort_event.set() — 让我们的 conversation_history 注入逻辑可检查
    """
    evt = get_abort_event(api_key, base_url, model)
    evt.set()
    try:
        from tools.interrupt import set_interrupt as _set_interrupt
        _set_interrupt()
    except Exception:
        pass


def clear_abort(api_key=None, base_url=None, model=None):
    """在每次新对话开始前重置中止状态。"""
    evt = get_abort_event(api_key, base_url, model)
    evt.clear()

def _shortid(prefix: str = "id") -> str:
    """生成简短 ID（10 字符随机），给 runId/messageId/toolCallId 用。"""
    import secrets
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    return f"{prefix}_{secrets.choice('abcdefghijklmnopqrstuvwxyz')}{secrets.token_hex(4)}"


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


class EventEmitter:
    """AG-UI 协议事件发射器（对齐官方 ag-ui 规范 v0.0.57）。

    官方规范要点（https://github.com/ag-ui-protocol/ag-ui）：
    - 每个事件可选 timestamp(ms epoch)；schema 为 passthrough，允许携带扩展字段
    - RUN_STARTED 必须含 threadId + runId；run 必须以 RUN_FINISHED 或 RUN_ERROR 结束（互斥）
    - RUN_ERROR 的 message 是顶层字符串字段（非嵌套对象）
    - STEP_STARTED/FINISHED 必须含 stepName
    - TOOL_CALL_START 必须含 toolCallId + toolCallName；TOOL_CALL_RESULT 必须含 messageId + content
    - 推理内容事件官方名为 REASONING_MESSAGE_CONTENT（THINKING_* 已废弃）

    项目自有扩展字段（stepId/kind/title/toolName/preview/citations 等）继续保留，
    供 LawClaw 前端的步骤面板/引用卡片使用；同时保留旧版 *_compat_callback 双发。
    """

    def __init__(self,
                 raw_send_fn=None,          # callable(dict) — 负责把 AG-UI 事件发到 wire
                 delta_compat_cb=None,
                 tool_start_compat_cb=None,
                 tool_complete_compat_cb=None,
                 thinking_compat_cb=None,
                 thread_id=None):           # AG-UI threadId（LawClaw 语义 = 会话 ID）
        self.send = raw_send_fn or (lambda evt: None)
        self.delta_cb = delta_compat_cb
        self.tool_start_cb = tool_start_compat_cb
        self.tool_complete_cb = tool_complete_compat_cb
        self.thinking_cb = thinking_compat_cb
        self.thread_id = str(thread_id) if thread_id else "default"
        # 内部记账：stepId → stepName / toolCallId → messageId（供 FINISHED/RESULT 事件补官方必填字段）
        self._step_names: dict = {}
        self._tool_msg_ids: dict = {}

    # ── core wire emitter ──
    def emit(self, evt: dict):
        """发送 AG-UI 事件到 wire（自动注入官方 timestamp，ms epoch）。"""
        try:
            import time as _time
            evt.setdefault("timestamp", int(_time.time() * 1000))
            self.send(evt)
        except Exception:
            pass

    # ── Run 边界 ──
    def run_started(self, run_id: str, thread_id=None):
        self.emit({
            "type": "RUN_STARTED",
            "runId": run_id,
            "threadId": str(thread_id or self.thread_id),
            "startedAt": _now_iso(),
        })

    def run_finished(self, run_id: str, outcome_type: str = "success",
                     final_response: str = "", citations: list = None,
                     interrupts=None, error=None):
        evt = {
            "type": "RUN_FINISHED",
            "runId": run_id,
            "threadId": self.thread_id,
            "finishedAt": _now_iso(),
            "outcome": {"type": outcome_type},
            "finalResponse": final_response,
            "citations": citations or [],
        }
        if interrupts:
            evt["outcome"]["interrupts"] = interrupts
        if error:
            evt["outcome"]["error"] = error if isinstance(error, dict) else {"message": str(error)}
        self.emit(evt)

    def run_error(self, run_id: str, error, code: str = ""):
        """官方 RUN_ERROR：message 为顶层字符串；run 必须以 RUN_ERROR 终止且不再发 RUN_FINISHED。"""
        if isinstance(error, dict):
            message = str(error.get("message") or error)
        else:
            message = str(error)
        evt = {
            "type": "RUN_ERROR",
            "message": message,
            "runId": run_id,
            "threadId": self.thread_id,
            "occurredAt": _now_iso(),
        }
        if code:
            evt["code"] = code
        self.emit(evt)

    # ── Step 进度 ──
    def step_started(self, run_id: str, step_id: str, step_index: int,
                     kind: str, title: str, description: str = ""):
        self._step_names[step_id] = title
        self.emit({
            "type": "STEP_STARTED",
            "stepName": title,
            "runId": run_id, "stepId": step_id,
            "stepIndex": step_index, "kind": kind,
            "title": title, "description": description or "",
            "startedAt": _now_iso(),
        })

    def step_finished(self, run_id: str, step_id: str, status: str = "ok", step_name: str = ""):
        self.emit({
            "type": "STEP_FINISHED",
            "stepName": step_name or self._step_names.get(step_id, "step"),
            "runId": run_id, "stepId": step_id,
            "status": status,
            "finishedAt": _now_iso(),
        })
        self._step_names.pop(step_id, None)

    # ── Text Message (assistant) ──
    def text_message_start(self, run_id: str, message_id: str, role: str = "assistant"):
        self.emit({
            "type": "TEXT_MESSAGE_START",
            "runId": run_id, "messageId": message_id, "role": role,
            "createdAt": _now_iso(),
        })

    def text_message_content(self, run_id: str, message_id: str, delta: str):
        if not delta:
            return
        # 新旧双发
        self.emit({
            "type": "TEXT_MESSAGE_CONTENT",
            "runId": run_id, "messageId": message_id, "delta": delta,
        })
        if self.delta_cb:
            try: self.delta_cb(delta)
            except Exception: pass

    def text_message_end(self, run_id: str, message_id: str,
                         citations: list = None, final_content: str = ""):
        evt = {
            "type": "TEXT_MESSAGE_END",
            "runId": run_id, "messageId": message_id,
            "citations": citations or [],
        }
        if final_content:
            evt["finalContent"] = final_content
        self.emit(evt)

    # ── Tool Call ──
    def tool_call_start(self, run_id: str, tool_call_id: str, message_id: str,
                        tool_name: str, description: str = "", args_preview=None):
        # 官方必填：toolCallId + toolCallName；messageId 的官方名是 parentMessageId
        self._tool_msg_ids[tool_call_id] = message_id
        self.emit({
            "type": "TOOL_CALL_START",
            "toolCallId": tool_call_id, "toolCallName": tool_name,
            "parentMessageId": message_id,
            "runId": run_id, "messageId": message_id,
            "toolName": tool_name, "description": description or "",
            "startedAt": _now_iso(),
        })
        if self.tool_start_cb:
            try: self.tool_start_cb(tool_name, args_preview)
            except Exception: pass

    def tool_call_args(self, run_id: str, tool_call_id: str, delta: str):
        if not delta: return
        self.emit({
            "type": "TOOL_CALL_ARGS",
            "runId": run_id, "toolCallId": tool_call_id, "delta": delta,
        })

    def tool_call_end(self, run_id: str, tool_call_id: str, final_args: str = ""):
        evt = {
            "type": "TOOL_CALL_END",
            "runId": run_id, "toolCallId": tool_call_id,
            "finishedAt": _now_iso(),
        }
        if final_args:
            evt["finalArgs"] = final_args
        self.emit(evt)

    def tool_call_result(self, run_id: str, tool_call_id: str, result,
                         display: str = "preview", preview: str = ""):
        # 官方必填：messageId + content（字符串化结果）；result/display/preview 为项目扩展
        self.emit({
            "type": "TOOL_CALL_RESULT",
            "messageId": self._tool_msg_ids.get(tool_call_id, ""),
            "toolCallId": tool_call_id,
            "content": preview or (str(result)[:2000] if result is not None else ""),
            "role": "tool",
            "runId": run_id,
            "result": result,
            "display": display,
            "preview": preview or "",
        })
        self._tool_msg_ids.pop(tool_call_id, None)

    # ── Reasoning / Thinking ──
    def reasoning_start(self, run_id: str, message_id: str):
        self.emit({
            "type": "REASONING_START",
            "runId": run_id, "messageId": message_id,
            "startedAt": _now_iso(),
        })

    def reasoning_content(self, run_id: str, message_id: str, delta: str):
        if not delta: return
        self.emit({
            "type": "REASONING_MESSAGE_CONTENT",   # 官方事件名（THINKING_*/REASONING_CONTENT 已废弃）
            "runId": run_id, "messageId": message_id, "delta": delta,
        })
        if self.thinking_cb:
            try: self.thinking_cb(delta)
            except Exception: pass

    def reasoning_end(self, run_id: str, message_id: str, encrypted_value: str = ""):
        evt = {
            "type": "REASONING_END",
            "runId": run_id, "messageId": message_id,
        }
        if encrypted_value:
            evt["encryptedValue"] = encrypted_value
        self.emit(evt)

    # ── Activity ──
    # ── Activity（官方 schema：绑定 messageId 的活动快照/增量）──
    def activity_snapshot(self, message_id: str, activity_type: str, content: dict):
        self.emit({
            "type": "ACTIVITY_SNAPSHOT",
            "messageId": message_id,
            "activityType": activity_type,
            "content": content,
            "replace": True,
        })

    def activity_delta(self, message_id: str, activity_type: str, patch: list):
        self.emit({
            "type": "ACTIVITY_DELTA",
            "messageId": message_id,
            "activityType": activity_type,
            "patch": patch,
        })


def handle_chat(message: str, api_key=None, base_url=None, model=None,
                system_prompt=None, matter_context=None, skill_id=None, files=None,
                profile=None, conversation_history=None,
                stream_callback=None, tool_start_callback=None, tool_complete_callback=None,
                thinking_callback=None,
                event_emitter=None, thread_id=None, matter_id=None,
                matter_documents=None, experience_items=None) -> dict:
    """处理用户对话（AG-UI 协议重构版）。"""
    # ── Step 计数器（Run 内第几步，每次 tool 调用、每轮 think 各加 1）──
    step_counter = {"value": 0}
    def _next_step_id(prefix="step"):
        step_counter["value"] += 1
        return _shortid(prefix), step_counter["value"]

    # ── 若无 event_emitter 则退化：仅使用兼容性回调 ──
    if event_emitter is None:
        event_emitter = EventEmitter(
            delta_compat_cb=stream_callback,
            tool_start_compat_cb=tool_start_callback,
            tool_complete_compat_cb=tool_complete_callback,
            thinking_compat_cb=thinking_callback,
            thread_id=thread_id,
        )

    try:
        # ── Run 开始 ──
        run_id = _shortid("run")
        msg_id = _shortid("msg")
        event_emitter.run_started(run_id, thread_id=thread_id)

        # 检查是否已被中止
        abort_evt = get_abort_event(api_key, base_url, model)
        if abort_evt.is_set():
            event_emitter.run_finished(run_id, "success", "⏸️ 已中止", [], error=None)
            return {"response": "⏸️ 已中止", "citations": [], "aborted": True}

        # 新对话开始前清空中止状态
        clear_abort(api_key, base_url, model)
        agent = get_agent(api_key, base_url, model)
        full_message = message
        ctx = matter_context
        if isinstance(ctx, str) and ctx.strip():
            # 兼容调用方以 JSON 文本传入（前端契约是 dict，但 RPC 客户端可能传序列化字符串；
            # 旧实现只认 dict，字符串会被静默丢弃，导致「案件上下文注入」无声失效）
            try:
                ctx = json.loads(ctx)
            except (ValueError, TypeError):
                ctx = None
        if isinstance(ctx, dict):
            ctx_lines = []
            for k, v in ctx.items():
                if not v:
                    continue
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                ctx_lines.append(f"{k}: {v}")
            if ctx_lines:
                full_message = "[案件上下文]\n" + "\n".join(ctx_lines) + "\n\n---\n" + message

        # Attach file contents for the LLM（文档抽取适配层：PDF/DOCX/XLSX 真实内容进 LLM）
        ctx_stats = {"history_rounds": 0, "kb_chunks": 0, "kb_docs": 0, "experience": 0, "files": 0}
        file_blocks = []
        if files and isinstance(files, list):
            import base64, tempfile
            for f in files:
                fname = f.get("name", "unknown")
                fdata = f.get("data", "")
                ftype = f.get("type", "")
                if fdata and fdata.startswith("data:"):
                    try:
                        _, encoded = fdata.split(",", 1)
                        decoded = base64.b64decode(encoded)
                        # 抽取适配链：pymupdf4llm → pymupdf → pdfminer；docx/xlsx/文本类各有专属后端
                        ext = doc_intel.extract_document_text(fname, decoded)
                        if ext.get("ok"):
                            ctx_stats["files"] += 1
                            text = ext["text"][:50000]
                            file_blocks.append(
                                f"[附件: {fname}（解析器: {ext['extractor']}，{ext['chars']} 字符）]\n```\n{text}\n```\n"
                            )
                        else:
                            why = ext.get("error") or "无可用解析器"
                            file_blocks.append(f"[附件: {fname} (无法解析: {why})]\n")
                    except Exception:
                        file_blocks.append(f"[附件: {fname} (无法解码)]\n")
        if file_blocks:
            full_message = full_message + "\n\n---\n用户上传的文件:\n" + "\n".join(file_blocks)

        # ── 案件知识库：按用户问题检索已解析的案件文档，注入最相关段落 ──
        if matter_documents and isinstance(matter_documents, list) and message:
            try:
                kb_res = doc_intel.kb_search(matter_id or thread_id or "default", message, matter_documents, top_k=5)
                chunks = kb_res.get("chunks", [])
                ctx_stats["kb_docs"] = kb_res.get("indexed_docs", 0)
                ctx_stats["kb_chunks"] = len(chunks)
                if chunks:
                    kb_block = "\n\n".join(
                        f"『{c['name']}』片段:\n{c['text']}" for c in chunks
                    )
                    full_message = (full_message + "\n\n---\n[案件文档库检索结果（自动召回，来源为该案件已解析文件）]\n"
                                    + kb_block)
            except Exception:
                pass

        # ── 经验记忆：跨案件相似经验/决策自动召回 ──
        if experience_items and isinstance(experience_items, list) and message:
            try:
                exp_res = doc_intel.experience_search(message, experience_items, top_k=3)
                hits = exp_res.get("hits", [])
                ctx_stats["experience"] = len(hits)
                if hits:
                    exp_block = "\n\n".join(
                        f"· [{h.get('matterTitle', '其他案件')}] {h.get('title', '')}"
                        + (f"\n  {h.get('text', '')[:200]}" if h.get("text") else "")
                        for h in hits
                    )
                    full_message = (full_message + "\n\n---\n[历史经验召回（自动检索的相似案件/决策记录，供参考）]\n"
                                    + exp_block)
            except Exception:
                pass

        # If a specific skill was activated, inject full SKILL.md workflow
        if skill_id:
            skill_content = _load_skill_content(skill_id)
            skill_name = skill_id
            skills_list = _skills_cache or []
            for s in skills_list:
                if s["id"] == skill_id:
                    skill_name = s["name"]
                    break
            if skill_content:
                combined_prompt = (system_prompt or LAWYER_SYSTEM_PROMPT) + (
                    f"\n\n[用户激活技能: {skill_name}]\n"
                    f"请严格遵循以下技能工作流指令执行，按步骤完成所有要求的操作：\n\n"
                    f"{skill_content}\n"
                )
            else:
                combined_prompt = (system_prompt or LAWYER_SYSTEM_PROMPT) + (
                    f"\n\n[用户激活技能: {skill_name}]\n"
                    f"用户明确要求使用「{skill_name}」技能。请遵循该技能的标准流程执行。"
                )
        else:
            # 注入执业画像到系统提示词（P0-3）
            combined_prompt = build_lawyer_system_prompt(profile, system_prompt)

        # ── 构建 OpenAI 格式的 conversation_history ──
        # 前端传入的 history 已是 [{role, content}, ...] 格式
        # 过滤掉空消息和当前用户消息（agent 会自己加），保留最多 20 轮防止 token 溢出
        clean_history = []
        if conversation_history and isinstance(conversation_history, list):
            for msg in conversation_history[-40:]:  # 保留最近 20 轮 = 40 条
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content and content.strip():
                    clean_history.append({"role": role, "content": str(content)})
            # 缓存前缀稳定：按完整对话对（user+assistant）对齐裁剪，
            # 避免每次越窗只丢 1 条导致前缀整体位移（上下文轮换的缓存杀手）
            if len(clean_history) and clean_history[0]["role"] == "assistant":
                clean_history = clean_history[1:]
            if len(clean_history) % 2 == 1:
                clean_history = clean_history[1:]
            ctx_stats["history_rounds"] = len(clean_history) // 2

        # ── P0/P1: 用 EventEmitter 包装回调（AG-UI 事件 + 旧格式双发） ──
        run_id_local = run_id
        msg_id_local = msg_id

        # 流式文本：TEXT_MESSAGE_START(首次 delta 触发) → *TEXT_MESSAGE_CONTENT
        _text_started = [False]
        def _agui_stream_cb(delta_text):
            if not delta_text:
                return
            if not _text_started[0]:
                _text_started[0] = True
                event_emitter.text_message_start(run_id_local, msg_id_local, "assistant")
            event_emitter.text_message_content(run_id_local, msg_id_local, delta_text)

        # 工具调用：对应 Step（kind='tool'）
        # NOTE: Hermes tool_executor 调用 signature（3 参数）：
        #   agent.tool_start_callback(tool_call_id: str, tool_name: str, args: dict|list|str)
        def _agui_tool_start_cb(tool_call_id, tool_name, args=None):
            sid, sidx = _next_step_id("step")
            title = f"调用工具：{_friendly_tool_name(tool_name)}"
            # args → 人类可读预览
            try:
                if args is None:
                    args_preview = ""
                elif isinstance(args, (dict, list)):
                    import json as _json
                    args_preview = _json.dumps(args, ensure_ascii=False)[:300]
                else:
                    args_preview = str(args)[:300]
            except Exception:
                args_preview = ""
            desc = f"工具标识：{tool_name}"
            if args_preview:
                desc += "  ·  参数预览：" + args_preview
            event_emitter.step_started(run_id_local, sid, sidx, "tool", title, desc)
            # 记录 (tool_call_id, sid, tool_name, args_preview) → 供 complete 阶段查
            _last_tc[0] = (tool_call_id, sid, tool_name, args_preview)
            event_emitter.tool_call_start(run_id_local, tool_call_id, msg_id_local, tool_name, desc, args_preview)

        # NOTE: Hermes tool_executor 调用 signature（4 参数）：
        #   agent.tool_complete_callback(tool_call_id: str, tool_name: str, args, function_result)
        def _agui_tool_complete_cb(tool_call_id, tool_name, args=None, function_result=None):
            rec = _last_tc[0]
            sid = None; nm = tool_name; args_preview = ""
            if rec:
                _tc, _sid, _nm, _args = rec
                sid = _sid
                if _nm: nm = _nm
                if _args: args_preview = _args
                # 如果 Hermes 第二次传来了新的 args 也优先用它
                try:
                    if args is not None and not args_preview:
                        if isinstance(args, (dict, list)):
                            import json as _json
                            args_preview = _json.dumps(args, ensure_ascii=False)[:300]
                        else:
                            args_preview = str(args)[:300]
                except Exception:
                    pass
            result_preview_text = ""
            try:
                if function_result is None:
                    result_preview_text = "(空)"
                elif isinstance(function_result, str):
                    result_preview_text = function_result[:1500]
                elif isinstance(function_result, (dict, list)):
                    import json as _json
                    result_preview_text = _json.dumps(function_result, ensure_ascii=False)[:1500]
                else:
                    result_preview_text = str(function_result)[:1500]
            except Exception:
                result_preview_text = "(无法预览)"

            if tool_call_id and sid:
                # ToolCallEnd + ToolCallResult + StepFinished
                try:
                    event_emitter.tool_call_end(run_id_local, tool_call_id, args_preview)
                    short_preview = (result_preview_text[:120] + "…") if len(result_preview_text) > 120 else result_preview_text
                    event_emitter.tool_call_result(
                        run_id_local, tool_call_id, function_result,
                        display="preview", preview=short_preview or f"{nm or tool_name} 执行完成"
                    )
                finally:
                    event_emitter.step_finished(run_id_local, sid, "ok")
                # 旧兼容（tool_complete_callback 直接派发）
                if event_emitter.tool_complete_cb:
                    try: event_emitter.tool_complete_cb(tool_name, function_result)
                    except Exception: pass
                _last_tc[0] = None

        # Thinking / Reasoning：对应 Step（kind='think'）
        _think_started = [False]
        _last_think_step = [None]
        def _agui_thinking_cb(thinking_text):
            if not thinking_text:
                return
            if not _think_started[0]:
                _think_started[0] = True
                event_emitter.reasoning_start(run_id_local, msg_id_local)
                sid, sidx = _next_step_id("step")
                _last_think_step[0] = sid
                event_emitter.step_started(run_id_local, sid, sidx, "think", "推理中…", "正在分析法律问题与检索策略")
            event_emitter.reasoning_content(run_id_local, msg_id_local, thinking_text)

        _last_tc = [None]

        agent.tool_start_callback = _agui_tool_start_cb
        agent.tool_complete_callback = _agui_tool_complete_cb
        agent.thinking_callback = _agui_thinking_cb

        # ── 会话隔离：把 agent 的 Hermes 会话绑定到前端会话 ID ──
        # 上游 run_conversation 只读 agent.session_id（不从参数赋值）；agent 实例按模型配置
        # 缓存共享，若不绑定，所有前端会话共用一个 Hermes 持久会话——新对话会带着旧对话记忆。
        if thread_id:
            agent.session_id = str(thread_id)

        # ── 调用 agent.run_conversation ──
        result = agent.run_conversation(
            full_message,
            system_message=combined_prompt or None,
            conversation_history=clean_history if clean_history else None,
            stream_callback=_agui_stream_cb,
        )

        # 清理回调，防止下一次请求复用时回调指向已关闭的 websocket
        agent.tool_start_callback = None
        agent.tool_complete_callback = None
        agent.thinking_callback = None

        # 若 thinking 启动了但未关闭 step：补一个 StepFinished
        if _think_started[0] and _last_think_step[0]:
            event_emitter.reasoning_end(run_id_local, msg_id_local)
            event_emitter.step_finished(run_id_local, _last_think_step[0], "ok")
            _last_think_step[0] = None

        # 检查中止状态
        if abort_evt.is_set():
            event_emitter.run_finished(run_id, "interrupt", "⏸️ 已中止", [])
            return {"response": "⏸️ 已中止", "citations": [], "aborted": True}

        # run_conversation 返回 dict，包含 final_response 等字段
        if isinstance(result, dict):
            response = result.get("final_response", "")
        else:
            response = str(result) if result else ""

        if not response:
            err = "AI 模型未返回有效响应，请检查 API Key 和网络连接。"
            citations = []
            # 补一个 TEXT_MESSAGE_START + END（保证即使没有 streaming 也有完整消息生命周期）
            if not _text_started[0]:
                event_emitter.text_message_start(run_id_local, msg_id_local, "assistant")
            event_emitter.text_message_end(run_id_local, msg_id_local, [], err)
            # 官方规范：RUN_ERROR 与 RUN_FINISHED 互斥，错误终止只发 RUN_ERROR
            event_emitter.run_error(run_id, err, code="empty_response")
            return {"response": err, "citations": [], "error": True}

        # 底层 API 报错有时会被 Hermes 捕获后塞进 final_response —— 识别并翻译
        if _looks_like_raw_api_error(response):
            response = _friendly_llm_error(response)
            event_emitter.run_error(run_id, response, code="llm_error")
            return {"response": response, "citations": [], "error": True}

        citations = extract_citations(response)
        # Final step：回复生成完成（kind='final'）
        sid, sidx = _next_step_id("step")
        event_emitter.step_started(run_id_local, sid, sidx, "final", "生成最终回复", "整理法律分析结果并引用法条")
        # 如完全未收到 streaming（同步模式）：补一个完整 text 生命周期
        if not _text_started[0]:
            event_emitter.text_message_start(run_id_local, msg_id_local, "assistant")
            event_emitter.text_message_content(run_id_local, msg_id_local, response)
        event_emitter.text_message_end(run_id_local, msg_id_local, citations, response)
        event_emitter.step_finished(run_id_local, sid, "ok")

        event_emitter.run_finished(run_id, "success", response, citations)
        return {"response": response, "citations": citations, "context_stats": ctx_stats}
    except Exception as e:
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        tb_str = buf.getvalue()
        sys.stderr.write(f"[handle_chat] ERROR:\n{tb_str}\n")
        sys.stderr.flush()
        friendly = _friendly_llm_error(str(e))
        try:
            if 'run_id' in locals():
                # 官方规范：错误终止只发 RUN_ERROR，不再补发 RUN_FINISHED
                event_emitter.run_error(run_id, friendly, code="exception")
        except Exception:
            pass
        return {"response": friendly, "citations": [], "error": True}


def _friendly_llm_error(raw: str) -> str:
    """把底层 LLM API 的原始报错翻译成中国律师能看懂、知道下一步做什么的中文提示。"""
    s = (raw or "").lower()
    if "429" in s or "rate limit" in s:
        return ("⏳ 模型服务限流：您的 API 额度已达到当前套餐上限（HTTP 429）。\n"
                "请稍等一两分钟再试；若频繁出现，请到「配置」更换 API Key 或升级套餐。")
    if "401" in s or "invalid api key" in s or "unauthorized" in s or "authentication" in s:
        return ("🔑 API Key 无效或已过期（HTTP 401）。\n"
                "请点击左下角「配置」检查并重新填写 API Key（可先点“测试连接”验证）。")
    if "insufficient" in s and ("balance" in s or "quota" in s) or "欠费" in s:
        return ("💳 API 账户余额不足，请前往服务商控制台充值后重试。")
    if "timeout" in s or "timed out" in s or "connection error" in s or "connect error" in s:
        return ("🌐 连接模型服务超时，请检查网络（代理/防火墙）后重试。")
    if "model" in s and ("not found" in s or "does not exist" in s):
        return ("❓ 模型名称不存在（HTTP 404）。请到「配置」核对模型名称拼写。")
    return f"⚠️ 调用模型服务失败：{(raw or '未知错误')[:200]}"


def _looks_like_raw_api_error(text: str) -> bool:
    """识别底层 API 报错被当作回复正文返回的情况（Hermes 捕获后放进 final_response）。"""
    t = (text or "").strip()
    return t.startswith("API call failed") or ("HTTP 4" in t and len(t) < 600)


def _friendly_tool_name(raw: str) -> str:
    """把 Hermes 工具名（如 'mcp_yuandian_law_yuandian_rh_ft_search'）转成中文友好名。"""
    if not raw:
        return "未知工具"
    name = raw.lower()
    # 元典 MCP 前缀
    if name.startswith("mcp_yuandian"):
        if "case" in name: return "元典案例检索"
        if "company" in name: return "元典工商查询"
        if "search" in name or "ft_" in name: return "元典法规检索"
        return "元典开放平台"
    if "legal_search" in name: return "法律检索"
    if "contract" in name: return "合同审查"
    if "draft" in name: return "文书起草"
    if "evidence" in name: return "证据分析"
    if "fee" in name or "calculator" in name: return "费用/期限计算"
    # 兜底：取下划线最后一节并去 _ 前缀
    parts = raw.split("_")
    return parts[-1] if len(parts) <= 3 else "_".join(parts[-3:])

# ── 检索查询改写：口语 → 法言法语 ──
# 元典检索对法言法语敏感（"买卖合同 违约责任"可命中，"违约金太高怎么办"返回 0 条）。
# 策略：① 规则短语替换（零成本）；② 仍 0 结果时用 LLM 改写重试一次（短超时，失败回退原查询）。

_COLLOQUIIAL_RULES = [
    ("不续签", "劳动合同期满终止 经济补偿"),
    ("不续订", "劳动合同期满终止 经济补偿"),
    ("有补偿吗", "经济补偿"),
    ("有赔偿吗", "损害赔偿"),
    ("违约金过高", "违约金过分高于造成的损失 调整"),
    ("违约金太高", "违约金过分高于造成的损失 调整"),
    ("违约金过低", "违约金 予以增加"),
    ("怎么分财产", "夫妻共同财产分割"),
    ("怎么分", "分割"),
    ("起诉流程", "起诉条件 立案"),
    ("怎么起诉", "起诉条件 立案"),
    ("被辞退", "违法解除劳动合同 赔偿金"),
    ("被开除了", "违法解除劳动合同 赔偿金"),
    ("拖欠工资", "未及时足额支付劳动报酬"),
    ("借钱不还", "民间借贷 偿还借款"),
    ("不还钱", "民间借贷 偿还借款"),
    ("房屋漏水", "建筑物区分所有权 保修责任"),
    ("楼上漏水", "相邻关系 损害赔偿"),
]

_QUESTION_FILLERS = ["请问", "咨询一下", "想知道", "帮忙", "谢谢", "一下", "如何", "怎么办", "怎么处理", "能", "吗", "呢", "？", "?"]

def _rule_rewrite_query(query: str) -> str:
    q = (query or "").strip()
    # 规则命中 → 整句替换为规范检索词（子串原位替换会产生拼接复读）
    for colloquial, legal in _COLLOQUIIAL_RULES:
        if colloquial in q:
            return legal
    # 无规则命中：仅去疑问填充词
    for w in _QUESTION_FILLERS:
        q = q.replace(w, "")
    q = re.sub(r"\s+", " ", q).strip()
    return q or (query or "").strip()

def _llm_rewrite_query(query: str, search_type: str):
    """LLM 把口语问题改写成检索关键词；任何失败返回 None（调用方回退原查询）。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    model = os.getenv("LAWCLAW_MODEL", DEFAULT_MODEL)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=8)
        scene = "中国法律法规库" if search_type != "case" else "中国裁判文书案例库"
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content":
                    f"把用户的口语化法律问题改写成适合在{scene}检索的3-6个中文关键词，用空格分隔。"
                    "只输出关键词本身，不要任何解释、标点或前后缀。"},
                {"role": "user", "content": query},
            ],
            max_tokens=60,
            temperature=0.1,
        )
        kw = (resp.choices[0].message.content or "").strip().strip('"「」『\'。.')
        if kw and 1 < len(kw) <= 60 and "\n" not in kw:
            return kw
    except Exception:
        return None
    return None

# ════════════════════════════════════════════════
#  元典 MCP 深度检索（权威案例 / 援引法条反查类案）
#  经 tools.registry.dispatch 调用已注册的 MCP 工具（内部走 MCP loop + 护栏）
#  依据《元典MCP实务操作指南》实测口径：yyft 为「全称+中文数字条号」数组
# ════════════════════════════════════════════════

def _parse_law_query(query: str):
    """「民法典 第917条」/「中华人民共和国民法典 第九百一十七条」→ (全称, 全称+中文条号)。"""
    import re as _re
    q = (query or "").strip()
    m = _re.match(r"^(.*?法|.*?条例|.*?解释|.*?规定|.*?民法典)\s*第([0-9一二三四五六七八九十百千零]+)条\s*(?:第([0-9一二三四五六七八九十百千零]+)款)?$", q)
    if not m:
        return q, None
    law, art, sub = m.group(1), m.group(2), m.group(3)
    if not law.startswith("中华人民共和国"):
        law = "中华人民共和国" + law
    def _cn(x):
        return x if not x.isdigit() else _num_to_cn(int(x))
    ft = f"{law}第{_cn(art)}条" + (f"第{_cn(sub)}款" if sub else "")
    return law, ft


def _call_mcp_case_tool(tool_short: str, args: dict) -> dict:
    """调用 yuandian-case MCP 工具并解析结果（静默错误加固：检查 code/message 与空列表）。"""
    from tools.registry import registry
    full_name = f"mcp__yuandian_case__yuandian_rh_{tool_short}"
    raw = registry.dispatch(full_name, args)
    if isinstance(raw, dict):  # dispatch 异常规范化的 {"error": ...}
        raise RuntimeError(raw.get("error", "MCP 调用失败"))
    payload = json.loads(raw)
    text = payload.get("result", "")
    if payload.get("structuredContent") and not text:
        text = json.dumps(payload["structuredContent"], ensure_ascii=False)
    try:
        parsed = json.loads(text) if isinstance(text, str) and text.strip().startswith(("{", "[")) else None
    except ValueError:
        parsed = None
    # 元典静默错误：code=200 但 message「未查询到相关内容」≠ 查到
    msg = ""
    items = []
    if isinstance(parsed, dict):
        msg = parsed.get("message") or parsed.get("msg") or ""
        data = parsed.get("data")
        if isinstance(data, dict):
            items = data.get("lst") or data.get("list") or data.get("rows") or []
        elif isinstance(data, list):
            items = data
    elif isinstance(parsed, list):
        items = parsed
    return {"items": items, "message": msg, "total": parsed.get("data", {}).get("total") if isinstance(parsed, dict) else None}


def handle_legal_search_authoritative(query: str) -> dict:
    """权威案例检索（yuandian_rh_qwal_search）：指导性/公报/参考/典型案例 + 官方要旨。"""
    result = _call_mcp_case_tool("qwal_search", {
        "qw": query, "search_mode": "and",
        "source": ["指导性案例", "公报案例", "参考案例", "典型案例"],
        "pageSize": 10, "pageNo": 1,
    })
    results = []
    for it in result["items"][:10]:
        content = it.get("llm_content") or it.get("zy") or it.get("content") or ""
        case_no = it.get("ah") or (content.split("##")[0].strip() if "##" in content.splitlines()[0] else "")
        src = it.get("source") or it.get("lb") or ""
        src_label = "、".join(src) if isinstance(src, list) else (src or "权威案例")
        results.append({
            "title": it.get("title") or it.get("bt") or (content.splitlines()[0].split("##")[0][:60]),
            "case_no": case_no,
            "source": "元典·权威案例（" + src_label + "）",
            "publish_date": it.get("cprq") or it.get("ja") or "",
            "court": it.get("fbdw") or it.get("jbdw") or "",
            "summary": content[:320],
            "raw": {k: it.get(k) for k in ("ay", "ajlb", "fbdw") if it.get(k)},
        })
    return {"results": results, "total": result.get("total") or len(results), "query_used": query,
            "note": result["message"] if not results else ""}


def handle_legal_search_by_law(query: str) -> dict:
    """援引法条反查类案（yuandian_rh_ptal_search yyft）：该法条被哪些判例引用。"""
    law, ft = _parse_law_query(query)
    if not ft:
        return {"results": [], "total": 0,
                "error": "请按「法律名 条号」输入，如：民法典 第九百一十七条（或 民法典 第917条）"}
    result = _call_mcp_case_tool("ptal_search", {"yyft": [ft], "pageSize": 10, "pageNo": 1})
    results = []
    for it in result["items"][:10]:
        content = it.get("llm_content") or it.get("ay") or it.get("content") or ""
        case_no = it.get("ah") or (content.split("##")[0].strip() if "##" in content.splitlines()[0] else "")
        results.append({
            "title": it.get("title") or it.get("bt") or (content.splitlines()[0].split("##")[0][:60]),
            "case_no": case_no,
            "court": it.get("fbdw") or it.get("jbdw") or "",
            "publish_date": it.get("cprq") or it.get("ja") or "",
            "source": "元典·裁判文书（援引法条反查）",
            "summary": content[:320],
            "raw": {k: it.get(k) for k in ("ay", "ajlb", "wslx") if it.get(k)},
        })
    return {"results": results, "total": result.get("total") or len(results), "query_used": query, "ft_used": ft,
            "note": result["message"] if not results else ""}


def handle_legal_search(query: str, search_type: str = "law") -> dict:
    """Search Chinese laws using 元典开放平台 (free, requires YUANDIAN_API_KEY).
    Falls back to a static pre-bundled law index if no API key is configured."""
    # 深度检索通道（元典 MCP）：权威案例 / 法条反查类案
    if search_type == "authoritative":
        return handle_legal_search_authoritative(query)
    if search_type == "case-by-law":
        return handle_legal_search_by_law(query)
    import requests as req_lib
    yuandian_key = os.environ.get("YD_OPEN_API_KEY") or os.environ.get("YUANDIAN_API_KEY")
    if yuandian_key:
        def _call(keyword: str):
            payload = {"keyword": keyword, "pageNo": 1, "pageSize": 10}
            if search_type == "case":
                payload["wslx"] = "case"
            resp = req_lib.post(
                "https://open.chineselaw.com/open/rh_fg_search",
                json=payload,
                headers={"X-API-Key": yuandian_key, "Content-Type": "application/json"},
                timeout=15,
            )
            data = resp.json()
            items = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else (data.get("data") or [])
            results = []
            for item in items:
                results.append({
                    "title": item.get("fgmc", ""),
                    "publish_date": item.get("fbrq", ""),
                    "department": item.get("jgmc", ""),
                    "source": "元典开放平台",
                    "effective": item.get("sxx", "有效") == "有效",
                    "doc_id": item.get("id", ""),
                })
            return results

        keyword = _rule_rewrite_query(query)
        rewritten = keyword != (query or "").strip()
        try:
            results = _call(keyword)
            # 规则改写后仍 0 结果 → LLM 改写重试一次
            if not results:
                kw2 = _llm_rewrite_query(query, search_type)
                if kw2 and kw2 != keyword:
                    retry = _call(kw2)
                    if retry:
                        keyword, rewritten, results = kw2, True, retry
            return {"results": results, "source": "yuandian", "query_used": keyword, "rewritten": rewritten}
        except Exception as e:
            return {"error": str(e), "results": [], "source": "yuandian"}
    return {"results": [], "source": "unconfigured", "note": "需要配置 YUANDIAN_API_KEY 或 YD_OPEN_API_KEY 环境变量"}

# ── 法条有效性验证 ──

# 已废止法律数据库（截至 2026-08）
# 民法典 2021-01-01 生效时废止了 9 部法律

def handle_verify_citation(law: str, article: str = "") -> dict:
    """验证法条是否现行有效。

    优先检查本地 DEPRECATED_LAWS 数据库（已废止法律），命中则直接返回。
    未命中则调用元典开放平台查询实时状态。
    """
    if not law:
        return {"valid": False, "error": "未提供法条名称"}

    # 1. 本地已废止法律快速检查
    if law in DEPRECATED_LAWS:
        dep = DEPRECATED_LAWS[law]
        return {
            "valid": False,
            "deprecated": True,
            "law_name": law,
            "status": "已废止",
            "replaced_by": dep["replaced_by"],
            "effective_until": dep["effective_until"],
            "note": dep["note"],
            "source": "本地废止法律数据库",
        }

    # 2. 主源：国家法律法规数据库（flk.npc.gov.cn，官方、免费、无认证）
    #    有效性是「法规级」属性：搜索只用法名（剥离条号），候选按规范化名称
    #    最短贴近匹配（防"民法典"误命中含该简称的司法解释）。
    #    sxx 官方口径：3=有效 2=已修改 1=已废止 4=未生效。
    try:
        npc = npc_law.find_law_status(law)
        if npc:
            valid_map = {3: True, 2: True, 1: False, 4: None}
            return {
                "valid": valid_map.get(npc["sxx"], None),
                "deprecated": npc["sxx"] == 1,
                "law_name": npc["title"],
                "status": npc["status"],
                "publish_date": npc["gbrq"],
                "effective_from": npc["sxrq"],
                "matched_article": article or "",
                "bbbs": npc["bbbs"],
                "source": "国家法律法规数据库",
            }
    except Exception as npc_err:
        print(f"[verify_citation] NPC 主源失败，回退元典: {npc_err}")  # 主源故障不阻塞

    # 3. 兜底源：元典开放平台
    #    keyword 只用法名（剥离条号），否则全文检索被条文号稀释（2026-09-11 实测）。
    yuandian_key = os.environ.get("YD_OPEN_API_KEY") or os.environ.get("YUANDIAN_API_KEY")
    if not yuandian_key:
        return {"valid": None, "error": "未配置元典 API Key，无法验证"}

    def _norm_law(name: str) -> str:
        """规范化法规名用于比对：去书名号/括号/空白/国名前缀。"""
        import re as _re
        return _re.sub(r"[《》〈〉（）()\s]|中华人民共和国", "", name or "")

    try:
        import requests as req_lib
        keyword = _norm_law(law) or law
        resp = req_lib.post(
            "https://open.chineselaw.com/open/rh_fg_search",
            json={"keyword": keyword, "pageNo": 1, "pageSize": 10},
            headers={"X-API-Key": yuandian_key, "Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"},
            timeout=10,
        )
        data = resp.json()
        items = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else (data.get("data") or [])
        law_norm = _norm_law(law)
        candidates = [
            it for it in items
            if (fg := it.get("fgmc", ""))
            and (law_norm in _norm_law(fg) or _norm_law(fg) in law_norm)
        ]
        if candidates:
            # 取名称最短（最贴近所查法规本体）的候选——防止"民法典"误命中
            # "最高人民法院关于适用《民法典》XX编的解释"等含简称的关联文件
            item = min(candidates, key=lambda it: len(it.get("fgmc", "")))
            fgmc = item.get("fgmc", "")
            sxx = item.get("sxx", "")
            is_valid = sxx in ("现行有效", "有效", "已修正", "已修订")
            is_deprecated = sxx in ("已废止", "失效", "已失效")
            return {
                "valid": is_valid,
                "deprecated": is_deprecated,
                "law_name": fgmc,
                "status": sxx,
                "publish_date": item.get("fbrq", ""),
                "department": item.get("jgmc", ""),
                "matched_article": article or "",
                "source": "元典开放平台",
            }
        return {"valid": None, "error": f"未找到匹配的法规: {law}", "searched": keyword}
    except Exception as e:
        return {"valid": None, "error": str(e)}

# ── 案件阶段 → 技能推荐 ──
STAGE_SKILL_MAP = {
    "待处理": [
        {"id": "litigation-matter-intake", "name": "案件登记", "icon": "📝", "reason": "新案件需要完成统一登记流程"},
        {"id": "litigation-cold-start-interview", "name": "利益冲突检索", "icon": "⚠️", "reason": "接案前必须完成利益冲突审查"},
    ],
    "审查中": [
        {"id": "litigation-matter-briefing", "name": "案件简报", "icon": "📋", "reason": "梳理案件事实与争议焦点"},
        {"id": "commercial-review", "name": "合同审查", "icon": "📑", "reason": "审查相关合同条款的法律风险"},
        {"id": "prc-legal-research-law-search", "name": "法规检索", "icon": "🔍", "reason": "检索适用法律条文"},
    ],
    "证据收集": [
        {"id": "litigation-cn-evidence-review", "name": "证据审查", "icon": "🔍", "reason": "系统化审查证据链完整性与证明力"},
        {"id": "litigation-chronology", "name": "时间线梳理", "icon": "📅", "reason": "建立案件事实时间线"},
        {"id": "litigation-claim-chart", "name": "诉讼请求矩阵", "icon": "📊", "reason": "对照诉讼请求梳理证据支持"},
    ],
    "诉讼中": [
        {"id": "litigation-brief-section-drafter", "name": "代理词起草", "icon": "✍️", "reason": "撰写代理词各章节"},
        {"id": "litigation-demand-draft", "name": "诉求文书", "icon": "📜", "reason": "起草起诉状/答辩状/上诉状"},
        {"id": "litigation-deposition-prep", "name": "庭审准备", "icon": "⚖️", "reason": "准备举证质证提纲与庭审策略"},
    ],
    "执行中": [
        {"id": "litigation-matter-briefing", "name": "案件简报", "icon": "📋", "reason": "梳理执行依据与被执行人财产线索"},
        {"id": "litigation-demand-draft", "name": "执行申请书", "icon": "📜", "reason": "起草执行申请/追加被执行人申请"},
        {"id": "litigation-matter-close", "name": "案件归档", "icon": "📦", "reason": "执行完毕后结案归档与经验总结"},
    ],
    "调解中": [
        {"id": "litigation-demand-draft", "name": "调解协议", "icon": "🤝", "reason": "起草调解协议书"},
        {"id": "litigation-demand-received", "name": "诉求分析", "icon": "📎", "reason": "分析对方调解方案"},
    ],
    "已完成": [
        {"id": "litigation-matter-close", "name": "案件归档", "icon": "📦", "reason": "完成结案归档与经验总结"},
    ],
    "已归档": [],
}

# ── 文书导出 Word (.docx) ──
# 把 Markdown 文书（对话产出/案件文件中的 .md）转换为可提交的 Word 文档。
# 字体遵循中文法律文书惯例：正文宋体、标题黑体、西文 Times New Roman。

def _docx_add_runs(para, text: str):
    """解析行内 Markdown（**粗体** / *斜体* / `代码`）为 docx runs。"""
    import re as _re
    token_re = _re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)")
    for tok in token_re.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            r = para.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = para.add_run(tok[1:-1]); r.italic = True
        elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            r = para.add_run(tok[1:-1]); r.font.name = "Consolas"
        else:
            para.add_run(tok)

def handle_export_docx(title: str = "", markdown: str = "", matter_title: str = "") -> dict:
    try:
        import base64
        import io
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.oxml.ns import qn
    except ImportError:
        return {"ok": False, "error": "服务器缺少 python-docx 库（pip install python-docx）"}

    try:
        doc = Document()
        # ── 全局中文字体：正文 宋体12 / 西文 Times New Roman ──
        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        # 页边距（公文惯例：上下 2.54cm，左右 3.17cm → 简化为 2.5/2.8）
        for sec in doc.sections:
            sec.top_margin = Cm(2.5); sec.bottom_margin = Cm(2.5)
            sec.left_margin = Cm(2.8); sec.right_margin = Cm(2.8)

        # ── 文书标题（黑体居中） ──
        doc_title = (title or "法律文书").strip()
        p = doc.add_paragraph()
        p.alignment = 1  # center
        r = p.add_run(doc_title)
        r.bold = True; r.font.size = Pt(16)
        r.font.name = "Times New Roman"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        if matter_title:
            p2 = doc.add_paragraph()
            p2.alignment = 1
            r2 = p2.add_run(f"（{matter_title}）")
            r2.font.size = Pt(10.5)
            r2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        # ── 逐行解析 Markdown ──
        in_code = False
        for raw_line in (markdown or "").splitlines():
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                cp = doc.add_paragraph()
                cr = cp.add_run(line)
                cr.font.name = "Consolas"; cr.font.size = Pt(10)
                continue
            if not line.strip():
                continue
            if line.startswith("### "):
                h = doc.add_heading(line[4:].strip(), level=3)
                h.style.font.name = "Times New Roman"
            elif line.startswith("## "):
                h = doc.add_heading(line[3:].strip(), level=2)
                h.style.font.name = "Times New Roman"
            elif line.startswith("# "):
                h = doc.add_heading(line[2:].strip(), level=1)
                h.style.font.name = "Times New Roman"
            elif line.strip() in ("---", "***", "___"):
                continue  # 分隔线 → 跳过（避免怪异横线）
            elif line.lstrip().startswith(("- ", "* ", "+ ")):
                p = doc.add_paragraph(style="List Bullet")
                _docx_add_runs(p, line.lstrip()[2:].strip())
            elif len(line) > 3 and line.lstrip()[0].isdigit() and line.lstrip()[1:3] in (". ", "、"):
                p = doc.add_paragraph(style="List Number")
                _docx_add_runs(p, line.lstrip().split(" ", 1)[-1].strip())
            elif line.lstrip().startswith(">"):
                p = doc.add_paragraph()
                pr = p.add_run(line.lstrip().lstrip(">").strip())
                pr.italic = True
                p.paragraph_format.left_indent = Cm(0.75)
            elif line.lstrip().startswith("|"):
                p = doc.add_paragraph()
                _docx_add_runs(p, line.strip())
                for run in p.runs:
                    run.font.size = Pt(10.5)
            else:
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Pt(24)  # 首行缩进两字符
                _docx_add_runs(p, line.strip())

        buf = io.BytesIO()
        doc.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        safe_title = re.sub(r'[\\/:*?"<>|\s]+', "_", doc_title)[:40] or "document"
        return {"ok": True, "filename": f"{safe_title}.docx", "data": b64}
    except Exception as e:
        return {"ok": False, "error": f"转换失败: {e}"}


def handle_recommend_skills_for_stage(stage: str) -> dict:
    """根据案件阶段返回推荐技能列表。"""
    skills = STAGE_SKILL_MAP.get(stage, [])
    return {"stage": stage, "recommended_skills": skills}

# ── 诉讼时效计算 ──
LIMITATION_RULES = {
    # ── 民事 ──
    "民事-一般": {"years": 3, "law": "民法典第188条第1款",
                  "note": "普通诉讼时效三年，自权利人知道或应当知道权利受到损害及义务人之日起计算。可因起诉、请求、承认、履行而中断；因不可抗力等中止。"},
    "民事-最长保护期": {"years": 20, "law": "民法典第188条第2款",
                       "note": "自权利被侵害之日起算，不适用诉讼时效中止、中断。超过20年人民法院不予保护，特殊情况可申请延长。"},
    "合同": {"years": 3, "law": "民法典第188、189条",
             "note": "适用3年普通时效；分期履行的合同自最后一期履行期限届满之日起算。"},
    "侵权": {"years": 3, "law": "民法典第188条",
             "note": "自受害人知道或应当知道权利受损害及义务人之日起算；人身损害自治疗终结或确诊之日起算。"},
    # ── 劳动争议（《劳动争议调解仲裁法》第27条）──
    "劳动-一般": {"years": 1, "law": "劳动争议调解仲裁法第27条第1款",
                  "note": "自当事人知道或应当知道其权利被侵害之日起一年内申请仲裁。适用于解除劳动合同、工资差额（非拖欠）、工伤待遇、年休假等争议。"},
    "劳动-报酬离职": {"years": 1, "law": "劳动争议调解仲裁法第27条第4款",
                     "note": "劳动关系终止的，应当自劳动关系终止之日起一年内提出。注意起算点是离职之日，而非欠薪发生之日。"},
    # 注：劳动-报酬在职 不受时效限制，由前端特殊处理，不在此字典内
    # ── 行政诉讼（《行政诉讼法》第46条）──
    "行政-一般": {"months": 6, "law": "行政诉讼法第46条第1款",
                  "note": "自知道或者应当知道作出行政行为之日起六个月内提起诉讼。"},
    "行政-未告知诉权": {"months": 12, "law": "行政诉讼法第46条 + 最高法解释第65条",
                       "note": "行政机关未告知起诉期限的，自知道或者应当知道起诉期限之日起一年内提起；但从知道或者应当知道行政行为内容之日起最长不得超过一年。"},
    "行政-不动产": {"years": 20, "law": "行政诉讼法第46条第2款",
                   "note": "因不动产提起诉讼的案件，自行政行为作出之日起超过二十年不予受理。起算点是行政行为作出之日，非知道之日。"},
    "行政-其他最长": {"years": 5, "law": "行政诉讼法第46条第2款",
                    "note": "非不动产案件自行政行为作出之日起超过五年提起诉讼的，人民法院不予受理。"},
    # ── 行政复议 ──
    "行政复议": {"days": 60, "law": "行政复议法第9条",
                "note": "自知道具体行政行为之日起六十日内提出。可因不可抗力等正当理由申请延长。"},
    # ── 国家赔偿 ──
    "国家赔偿": {"years": 2, "law": "国家赔偿法第39条",
                "note": "自国家机关及其工作人员行使职权时的行为被依法确认为违法之日起两年内。被羁押期间不计算在内；行为持续的，自行为终止之日起算。"},
    # ── 保险（《保险法》第26条）──
    "保险-非人寿": {"years": 2, "law": "保险法第26条第1款",
                   "note": "人寿保险以外的其他保险，被保险人或受益人请求赔偿或给付保险金的诉讼时效两年，自知道或者应当知道保险事故发生之日起计算。"},
    "保险-人寿": {"years": 5, "law": "保险法第26条第2款",
                 "note": "人寿保险的被保险人或受益人请求给付保险金的诉讼时效五年，自知道或者应当知道保险事故发生之日起计算。"},
    # ── 票据（《票据法》第17条）──
    "票据-追索": {"months": 6, "law": "票据法第17条第1项",
                  "note": "持票人对前手的追索权，自被拒绝承兑或者被拒绝付款之日起六个月不行使而消灭。"},
    "票据-再追索": {"months": 3, "law": "票据法第17条第4项",
                    "note": "持票人行使追索权清偿债务后，对其前手的再追索权，自清偿日或者被提起诉讼之日起三个月不行使而消灭。"},
    # ── 海商 ──
    "海商": {"years": 1, "law": "海商法第257条",
             "note": "就海上货物运输向承运人要求赔偿的请求权，时效期间为一年，自承运人交付或者应当交付货物之日起计算。"},
}

def handle_calc_limitation(case_type: str, event_date: str) -> dict:
    """计算诉讼时效届满日期。

    支持的 case_type 见 LIMITATION_RULES。特殊值：
    - "劳动-报酬在职" 由前端直接返回"不受时效限制"，不会进入此函数
    """
    if not case_type or not event_date:
        return {"error": "需要提供案件类型和事件日期"}
    rule = LIMITATION_RULES.get(case_type)
    if not rule:
        return {
            "error": f"未找到案件类型 '{case_type}' 的时效规则",
            "supported_types": list(LIMITATION_RULES.keys()),
        }
    try:
        from datetime import datetime
        base_date = datetime.strptime(event_date[:10], "%Y-%m-%d")
        deadline = None
        if "years" in rule:
            # 处理闰年2月29日：目标年若不是闰年，回退到2月28日
            try:
                deadline = base_date.replace(year=base_date.year + rule["years"])
            except ValueError:
                deadline = base_date.replace(year=base_date.year + rule["years"], day=28)
        elif "months" in rule:
            total_months = base_date.month + rule["months"]
            new_year = base_date.year + (total_months - 1) // 12
            new_month = (total_months - 1) % 12 + 1
            # 处理月末日期溢出（如1月31日 + 1个月 → 2月无31日）
            import calendar
            max_day = calendar.monthrange(new_year, new_month)[1]
            new_day = min(base_date.day, max_day)
            deadline = base_date.replace(year=new_year, month=new_month, day=new_day)
        elif "days" in rule:
            from datetime import timedelta
            deadline = base_date + timedelta(days=rule["days"])
        else:
            return {"error": "时效规则配置错误"}
        today = datetime.now()
        days_remaining = (deadline - today).days
        return {
            "case_type": case_type,
            "event_date": event_date[:10],
            "deadline": deadline.strftime("%Y-%m-%d"),
            "days_remaining": days_remaining,
            "status": "已过期" if days_remaining < 0 else ("紧急" if days_remaining <= 30 else "正常"),
            "law_basis": rule["law"],
            "note": rule["note"],
        }
    except Exception as e:
        return {"error": f"日期计算失败: {e}"}

# ── 期限智能引擎：考虑法定节假日顺延 ──
# 内置 2025-2027 年法定节假日数据（每年国务院办公厅发布后更新）
CHINESE_HOLIDAYS = {
    # 2026 年（参考 2025 年放假安排模式，实际以国务院发布为准）
    "2026-01-01": "元旦", "2026-02-08": "除夕", "2026-02-09": "春节",
    "2026-02-10": "春节", "2026-02-11": "春节", "2026-02-12": "春节",
    "2026-02-13": "春节", "2026-02-14": "春节", "2026-02-15": "春节",
    "2026-04-04": "清明", "2026-04-05": "清明", "2026-04-06": "清明",
    "2026-05-01": "劳动节", "2026-05-02": "劳动节", "2026-05-03": "劳动节",
    "2026-05-04": "劳动节", "2026-05-05": "劳动节",
    "2026-06-19": "端午", "2026-06-20": "端午", "2026-06-21": "端午",
    "2026-09-25": "中秋", "2026-09-26": "中秋", "2026-09-27": "中秋",
    "2026-10-01": "国庆", "2026-10-02": "国庆", "2026-10-03": "国庆",
    "2026-10-04": "国庆", "2026-10-05": "国庆", "2026-10-06": "国庆",
    "2026-10-07": "国庆", "2026-10-08": "国庆",
}

# 法定期限类型映射到天数
DEADLINE_TYPE_DAYS = {
    "filing": 7,                # 立案补正期限（一般 7 日）
    "evidence": 15,             # 举证期限（普通程序不少于 15 日）
    "defense": 15,              # 答辩期限（一审 15 日）
    "appeal-judgment": 15,      # 判决上诉期（民事/行政 15 日）
    "appeal-ruling": 10,        # 裁定上诉期（民事/行政 10 日）
    "appeal-criminal-judgment": 10,  # 刑事判决上诉期 10 日
    "appeal-criminal-ruling": 5,     # 刑事裁定上诉期 5 日
    "jurisdiction": 15,         # 管辖权异议答辩期
    "appraisal": 30,            # 鉴定申请期限（建议 30 日内）
    "preservation": 30,         # 财产保全期限（诉前 30 日内起诉）
    "enforcement": 730,         # 申请执行期限（2 年 = 730 日）
    "retrial": 180,             # 申请再审期限（6 个月 = 180 日）
    "arbitration-sue": 15,      # 劳动仲裁起诉期 15 日
}


def handle_calc_deadline(start_date: str, days: int = 0,
                          deadline_type: str = "custom",
                          skip_holidays: bool = True) -> dict:
    """期限智能计算引擎。

    支持三种模式：
    1. 指定天数：start_date + days → deadline
    2. 指定类型：start_date + deadline_type → 自动查表得 days → deadline
    3. 节假日顺延：若 deadline 落在周末或法定节假日，顺延至下一个工作日
       （法律依据：《民法典》第201条；期间届满日为节假日的，顺延至节假日后第一日）

    返回：
    - deadline: 截止日期（已顺延）
    - original_deadline: 顺延前日期
    - deferred: 是否发生顺延
    - deferred_reason: 顺延原因
    - weekend/holiday: 是否因周末/节假日顺延
    """
    from datetime import datetime, timedelta

    if not start_date:
        return {"error": "需要提供起始日期"}
    try:
        base = datetime.strptime(start_date[:10], "%Y-%m-%d")
    except Exception as e:
        return {"error": f"日期格式错误: {e}"}

    # 确定天数（客户端可能把天数传成字符串，统一容错为 int，避免 TypeError 冒成 -32603）
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 0
    if days <= 0 and deadline_type in DEADLINE_TYPE_DAYS:
        days = DEADLINE_TYPE_DAYS[deadline_type]
    if days <= 0:
        return {"error": "需要提供天数或有效的期限类型", "valid_types": list(DEADLINE_TYPE_DAYS.keys())}

    # 计算原始截止日（含当日次日算起的 N 天，对应"自送达/收到之日起 X 日内"）
    # 法律规则：期间开始的当日不计算在内，从下一日开始计算
    original = base + timedelta(days=days)

    deferred = False
    deferred_reason = ""
    final = original

    if skip_holidays:
        # 检查是否需要顺延（最多顺延 30 天防止死循环）
        for _ in range(30):
            weekday = final.weekday()  # 0=周一, 5=周六, 6=周日
            date_str = final.strftime("%Y-%m-%d")
            is_weekend = weekday >= 5
            is_holiday = date_str in CHINESE_HOLIDAYS

            if is_holiday:
                final = final + timedelta(days=1)
                deferred = True
                if not deferred_reason:
                    deferred_reason = f"届满日为法定节假日({CHINESE_HOLIDAYS[date_str]})"
            elif is_weekend:
                final = final + timedelta(days=1)
                deferred = True
                if not deferred_reason:
                    deferred_reason = f"届满日为周末"
            else:
                break

    today = datetime.now()
    days_remaining = (final - today).days

    return {
        "deadline": final.strftime("%Y-%m-%d"),
        "original_deadline": original.strftime("%Y-%m-%d"),
        "deferred": deferred,
        "deferred_reason": deferred_reason if deferred else "",
        "start_date": start_date[:10],
        "days": days,
        "deadline_type": deadline_type,
        "days_remaining": days_remaining,
        "status": "已过期" if days_remaining < 0 else ("紧急" if days_remaining <= 7 else "正常"),
        "law_basis": "《民法典》第201条：期间届满的最后一日为法定休假日的，以休假日后的第一日为期间届满的日期。",
    }


def handle_initialize(api_key=None, base_url=None, model=None):
    key = api_key or DEFAULT_API_KEY
    if key == "demo-mode":
        key = DEFAULT_API_KEY
    return {
        "status": "ok",
        "version": "0.1.0",
        "name": "LawClaw",
        "model": model or DEFAULT_MODEL,
        "provider": "agnes",
        "configured": bool(key),
    }

def handle_test_llm(api_key=None, base_url=None, model=None) -> dict:
    """真实调用一次最小补全，验证 API Key / 地址 / 模型可用（比 initialize 的"已配置"检查可靠）。

    返回 {ok, model, latency_ms?, message?}；错误信息经 _friendly_llm_error 本地化。
    """
    import time
    if not api_key or api_key == "demo-mode":
        api_key = DEFAULT_API_KEY
    base_url = base_url or DEFAULT_BASE_URL
    model = model or DEFAULT_MODEL
    if not api_key:
        return {"ok": False, "model": model, "message": "尚未配置 API Key，请先填写。"}
    t0 = time.time()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "回复两个字母：OK"}],
            max_tokens=16,
            temperature=0,
        )
        dt = int((time.time() - t0) * 1000)
        content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        return {"ok": True, "model": model, "latency_ms": dt, "sample": content[:20]}
    except Exception as e:
        return {"ok": False, "model": model, "message": _friendly_llm_error(str(e))}

def handle_list_mcp_servers() -> dict:
    import yaml
    config_path = BACKEND_DIR / ".hermes" / "config.yaml"
    if not config_path.exists():
        return {"servers": []}
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        servers = []
        for name, s in (cfg.get("mcp_servers") or {}).items():
            servers.append({
                "name": name,
                "url": s.get("url", ""),
                "enabled": s.get("enabled", True),
            })
        return {"servers": servers}
    except Exception as e:
        return {"error": str(e), "servers": []}

SKILLS_DIR = BACKEND_DIR / ".hermes" / "skills"

def _load_skill_content(skill_id: str) -> str:
    """Load full SKILL.md content (strip YAML frontmatter) for a given skill_id.
    skill_id can be 'legal/contract-review' or 'litigation-matter-intake'."""
    candidates = [
        SKILLS_DIR / skill_id / "SKILL.md",
        SKILLS_DIR / skill_id.replace("/", os.sep) / "SKILL.md",
    ]
    # Fallback: search by directory name match
    if not any(p.exists() for p in candidates):
        target_name = skill_id.split("/")[-1]
        for p in SKILLS_DIR.rglob("SKILL.md"):
            if p.parent.name == target_name:
                candidates.insert(0, p)
                break
    for path in candidates:
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                # Strip YAML frontmatter
                if raw.startswith("---"):
                    end = raw.find("---", 3)
                    if end != -1:
                        return raw[end + 3:].strip()
                return raw.strip()
            except Exception:
                pass
    return ""

def _parse_skill_md(path: Path) -> dict | None:
    """Parse a SKILL.md file and return {id, name, description, group}."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    # YAML frontmatter between --- markers
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    front = text[3:end].strip()
    # Extract name and description with simple line-by-line parsing
    name = ""
    description = ""
    desc_lines = []
    in_desc = False
    for line in front.split("\n"):
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            raw = line.split(":", 1)[1].strip()
            if raw.startswith(">"):
                in_desc = True
                continue
            description = raw.strip().strip('"').strip("'")
        elif in_desc:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("argument"):
                in_desc = False
                continue
            desc_lines.append(stripped)
    if desc_lines:
        description = " ".join(desc_lines)
    if not name:
        name = path.parent.name
    # Compute group from parent directory path
    # e.g. skills/legal/contract-review/SKILL.md → group: "legal"
    # e.g. skills/commercial-review/SKILL.md → group: "commercial"
    relative = path.relative_to(SKILLS_DIR) if SKILLS_DIR else path
    parts = relative.parts
    group = parts[0] if len(parts) >= 2 else "未分类"
    # Map flat names to readable groups
    GROUP_MAP = {
        "legal": "法律研究",
        "commercial": "商业合同",
        "litigation": "诉讼业务",
        "corporate": "公司业务",
        "prc": "中国法律研究",
        "divorce": "婚姻家事",
        "employment": "劳动人事",
        "ip": "知识产权",
        "ai-governance": "AI 治理",
        "privacy": "数据隐私",
        "regulatory": "监管合规",
        "product": "产品合规",
    }
    for prefix, label in GROUP_MAP.items():
        if name.startswith(prefix) or group.startswith(prefix):
            group = label
            break
    if group == "未分类":
        # Try to infer from name prefix
        if name.startswith("commercial"): group = "商业合同"
        elif name.startswith("litigation"): group = "诉讼业务"
        elif name.startswith("corporate"): group = "公司业务"
        elif name.startswith("prc"): group = "中国法律研究"
    id_str = str(relative.with_suffix("")).replace("\\", "/").replace("/SKILL", "")
    return {
        "id": id_str,
        "name": name,
        "description": description[:200] if description else "",
        "group": group,
        "icon": _skill_icon(name, group),
        "color": _skill_color(group),
    }

# Cache to avoid re-scanning on every request
_skills_cache = None

# 技能中文显示名：技能包 frontmatter 的 name 只有英文 id，直接展示对中国律师不友好。
# 此处维护 id → 中文名映射（与 handle_recommend_skills_for_stage 的命名保持一致）。
SKILL_DISPLAY_NAMES = {
    # LawClaw 基础技能
    # （legal/contract-review、legal/legal-research 已下线——由专业包 commercial-review / prc-legal-research-law-search 替代）
    "legal/fee-calculator": "诉讼费计算",
    "legal/document-draft": "文书起草",
    # 法律研究（元典数据）
    "prc-legal-research-law-search": "法规检索",
    "prc-legal-research-case-search": "类案检索",
    "prc-legal-research-deep-research": "深度法律研究",
    "prc-legal-research-company-search": "企业信息核查",
    # 执业画像冷启动访谈（LEGAL_AGENT_PROFILE_HOME）
    "litigation-cold-start-interview": "诉讼业务初始化访谈",
    "corporate-cold-start-interview": "公司业务初始化访谈",
    "commercial-cold-start-interview": "合同业务初始化访谈",
    # 诉讼业务
    "litigation-matter-intake": "收案评估",
    "litigation-matter-briefing": "案件简报",
    "litigation-matter-update": "案件进展更新",
    "litigation-matter-close": "结案报告",
    "litigation-cn-evidence-review": "证据审查分析",
    "litigation-demand-draft": "律师函起草",
    "litigation-demand-received": "律师函应对分析",
    "litigation-brief-section-drafter": "代理词起草",
    "litigation-deposition-prep": "庭审准备",
    "litigation-claim-chart": "诉讼请求图表",
    "litigation-chronology": "案件时间线梳理",
    # 公司业务
    "corporate-entity-compliance": "公司主体合规审查",
    "corporate-diligence-issue-extraction": "尽调问题提取",
    "corporate-board-minutes": "董事会决议纪要",
    "corporate-written-consent": "股东书面决议",
    # 商业合同
    "commercial-review": "商业合同审查",
    "commercial-nda-review": "保密协议（NDA）审查",
    "commercial-saas-msa-review": "SaaS/技术服务协议审查",
    "commercial-vendor-agreement-review": "供应商协议审查",
    # claude-for-legal-ZH 增量领域
    "employment-cold-start-interview": "劳动法插件初始化访谈",
    "employment-handbook-updates": "员工手册合规更新",
    "employment-hiring-review": "招聘录用合规审查",
    "employment-internal-investigation": "劳动合规内部调查",
    "employment-international-expansion": "跨国用工合规扩展",
    "employment-investigation-add": "调查记录追加",
    "employment-investigation-memo": "调查备忘录起草",
    "employment-investigation-open": "调查案件开启",
    "employment-investigation-query": "调查记录检索",
    "employment-investigation-summary": "调查摘要报告",
    "employment-leave-tracker": "假期追踪（三期/医疗期）",
    "employment-log-leave": "员工假期登记",
    "employment-policy-drafting": "劳动规章制度起草",
    "employment-termination-review": "解除劳动合同审查",
    "employment-wage-hour-qa": "工时加班合规答疑",
    "employment-worker-classification": "劳动关系认定分析",
    "employment-expansion-kickoff": "用工扩展合规启动",
    "employment-expansion-update": "用工扩展合规进展",
    "ip-cold-start-interview": "知识产权插件初始化访谈",
    "ip-cease-desist": "侵权警告函起草",
    "ip-clearance": "商标名称清查",
    "ip-fto-triage": "自由实施(FTO)初筛",
    "ip-infringement-triage": "知识产权侵权分诊",
    "ip-invention-intake": "发明交底登记",
    "ip-ip-clause-review": "知识产权条款审查",
    "ip-oss-review": "开源合规审查",
    "ip-portfolio": "知识产权组合盘点",
    "ip-takedown": "侵权内容下架通知",
    "ai-governance-cold-start-interview": "AI治理插件初始化访谈",
    "ai-governance-ai-inventory": "AI使用清单盘点",
    "ai-governance-aia-generation": "算法影响评估生成",
    "ai-governance-policy-monitor": "AI政策动态监控",
    "ai-governance-policy-starter": "AI治理政策起草",
    "ai-governance-reg-gap-analysis": "AI监管缺口分析",
    "ai-governance-use-case-triage": "AI应用场景分诊",
    "ai-governance-vendor-ai-review": "供应商AI方案审查",
    "privacy-cold-start-interview": "隐私合规初始化访谈",
    "privacy-dpa-review": "数据处理协议审查",
    "privacy-dsar-response": "个人信息查询响应",
    "privacy-pia-generation": "个人信息保护影响评估",
    "privacy-policy-monitor": "隐私政策动态监控",
    "privacy-reg-gap-analysis": "隐私监管缺口分析",
    "privacy-use-case-triage": "数据应用场景分诊",
    "regulatory-cold-start-interview": "监管合规初始化访谈",
    "regulatory-comments": "规章征求意见反馈",
    "regulatory-gap-surfacer": "监管要求浮现",
    "regulatory-gaps": "合规缺口梳理",
    "regulatory-policy-diff": "政策文件差异对比",
    "regulatory-policy-redraft": "政策文书改写",
    "regulatory-reg-feed-watcher": "监管动态追踪",
    "product-cold-start-interview": "产品合规初始化访谈",
    "product-feature-risk-assessment": "产品功能风险评估",
    "product-is-this-a-problem": "合规问题快判",
    "product-launch-review": "产品上线合规审查",
    "product-marketing-claims-review": "宣传用语合规审查",
}


def handle_list_hermes_skills() -> dict:
    global _skills_cache
    if _skills_cache is not None:
        return {"skills": _skills_cache}
    skills_dir = BACKEND_DIR / ".hermes" / "skills"
    if not skills_dir.exists():
        return {"skills": []}

    # Read enabled skills from config.yaml
    import yaml
    config_path = BACKEND_DIR / ".hermes" / "config.yaml"
    enabled_skills = set()
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            for skill_id in (cfg.get("skills") or {}).get("enabled") or []:
                enabled_skills.add(skill_id)
        except Exception:
            pass

    result = []
    for md_file in sorted(skills_dir.rglob("SKILL.md")):
        parsed = _parse_skill_md(md_file)
        if parsed:
            # Only include if it's in the enabled list (or no enabled list at all)
            if enabled_skills and parsed["id"] not in enabled_skills:
                continue
            # 英文 id → 中文显示名（技能包 frontmatter 无中文名）
            cn = SKILL_DISPLAY_NAMES.get(parsed["id"])
            if cn:
                parsed["name"] = cn
            result.append(parsed)
    _skills_cache = result
    return {"skills": result}

def _skill_icon(name: str, group: str) -> str:
    icon_map = {
        "legal": "📖", "commercial": "📋", "litigation": "⚖️",
        "corporate": "🏢", "prc": "🔍", "divorce": "💔",
    }
    for prefix, icon in icon_map.items():
        if group.startswith(prefix) or name.startswith(prefix):
            return icon
    if "review" in name or "scan" in name: return "🔍"
    if "draft" in name: return "📝"
    if "search" in name: return "🔎"
    if "research" in name: return "📚"
    if "close" in name: return "✅"
    if "intake" in name: return "📥"
    return "⚙️"

def _skill_color(group: str) -> str:
    color_map = {
        "法律研究": "#2a3f6a", "商业合同": "#2d7d4e", "诉讼业务": "#b22222",
        "公司业务": "#4a72a8", "中国法律研究": "#5a6a8a", "婚姻家事": "#d29922",
    }
    return color_map.get(group, "#6b7280")

def handle_request(method: str, params: dict) -> dict:
    # Extract streaming callbacks (injected by WsServer/StdinServer, not from client)
    stream_cb = params.pop("_stream_callback", None)
    tool_start_cb = params.pop("_tool_start_callback", None)
    tool_complete_cb = params.pop("_tool_complete_callback", None)
    thinking_cb = params.pop("_thinking_callback", None)
    # AG-UI 新版：EventEmitter 对象（WsServer/StdinServer 预构造注入）
    event_emitter = params.pop("event_emitter", None)

    if method == "initialize":
        return handle_initialize(params.get("api_key"), params.get("base_url"), params.get("model"))
    elif method == "test_llm":
        return handle_test_llm(params.get("api_key"), params.get("base_url"), params.get("model"))
    elif method == "ping":
        return {"pong": True}
    elif method == "chat":
        return handle_chat(
            params.get("message", ""),
            params.get("api_key"),
            params.get("base_url"),
            params.get("model"),
            params.get("system_prompt"),
            params.get("matter_context"),
            params.get("skill_id"),
            params.get("files"),
            params.get("profile"),
            params.get("conversation_history"),
            thread_id=params.get("thread_id"),
            matter_id=params.get("matter_id"),
            matter_documents=params.get("matter_documents"),
            experience_items=params.get("experience_items"),
            stream_callback=stream_cb,
            tool_start_callback=tool_start_cb,
            tool_complete_callback=tool_complete_cb,
            thinking_callback=thinking_cb,
            event_emitter=event_emitter,
        )
    elif method == "abort":
        # 真中止 RPC：让前端可主动终止后端 LLM 调用
        request_abort(params.get("api_key"), params.get("base_url"), params.get("model"))
        return {"status": "aborted"}
    elif method == "watchdog_sync":
        return {"synced": watchdog.sync_matters(params.get("matters") or [])}
    elif method == "watchdog_status":
        return watchdog.get_status()
    elif method == "watchdog_briefing":
        return watchdog.get_latest_briefing(params.get("job", "lawclaw-morning-briefing"))
    elif method == "watchdog_run_now":
        from cron import jobs as _cj
        jobs = {j.get("name"): j for j in _cj.list_jobs(include_disabled=True)}
        job = jobs.get(params.get("job", "lawclaw-morning-briefing"))
        if not job:
            return {"error": "值守任务不存在（可能被配置关闭）"}
        rec = _cj.trigger_job(job.get("id"))
        return {"triggered": bool(rec), "job": job.get("name"), "id": job.get("id")}
    elif method == "review_document":
        import doc_review as _doc_review
        return _doc_review.review_document(params.get("text", ""), bool(params.get("check_citations", True)))
    elif method == "npc_law_docx_url":
        import npc_law as _npc
        return {"url": _npc.get_docx_url(params.get("bbbs", ""), params.get("format", "docx"))}
    elif method == "legal_search_authoritative":
        return handle_legal_search_authoritative(params.get("query", ""))
    elif method == "legal_search_by_law":
        return handle_legal_search_by_law(params.get("query", ""))
    elif method == "legal_search":
        return handle_legal_search(params.get("query", ""), params.get("search_type", "law"))
    elif method == "verify_citation":
        return handle_verify_citation(params.get("law", ""), params.get("article", ""))
    elif method == "parse_document":
        import base64 as _b64
        fname = params.get("filename", "document")
        data_b64 = params.get("data_base64", "")
        try:
            raw = _b64.b64decode(data_b64) if data_b64 else b""
        except Exception:
            raw = b""
        return doc_intel.extract_document_text(fname, raw)
    elif method == "kb_search":
        return doc_intel.kb_search(
            params.get("matter_id", "default"),
            params.get("query", ""),
            params.get("documents", []),
            top_k=int(params.get("top_k", 5)),
        )
    elif method == "experience_search":
        return doc_intel.experience_search(
            params.get("query", ""),
            params.get("items", []),
            top_k=int(params.get("top_k", 4)),
        )
    elif method == "export_docx":
        return handle_export_docx(
            params.get("title", ""), params.get("markdown", ""), params.get("matter_title", "")
        )
    elif method == "recommend_skills_for_stage":
        return handle_recommend_skills_for_stage(params.get("stage", ""))
    elif method == "calc_limitation_period":
        return handle_calc_limitation(params.get("case_type", ""), params.get("event_date", ""))
    elif method == "calc_deadline":
        # 期限智能引擎：考虑节假日顺延
        return handle_calc_deadline(params.get("start_date", ""), params.get("days", 0),
                                     params.get("deadline_type", "custom"),
                                     params.get("skip_holidays", True))
    elif method == "list_mcp_servers":
        return handle_list_mcp_servers()
    elif method == "list_hermes_skills":
        return handle_list_hermes_skills()
    elif method == "setup_save":
        key = params.get("api_key", "")
        url = params.get("base_url", DEFAULT_BASE_URL)
        model = params.get("model", DEFAULT_MODEL)
        feishu_app_id = params.get("feishu_app_id", "")
        feishu_app_secret = params.get("feishu_app_secret", "")
        wecom_corp_id = params.get("wecom_corp_id", "")
        wecom_bot_id = params.get("wecom_bot_id", "")
        wecom_secret = params.get("wecom_secret", "")
        env_file = BACKEND_DIR / ".env"
        SKIP_PREFIXES = (
            "OPENAI_API_KEY=", "OPENAI_BASE_URL=", "LAWCLAW_MODEL=",
            "FEISHU_APP_ID=", "FEISHU_APP_SECRET=",
            "WECOM_CORP_ID=", "WECOM_BOT_ID=", "WECOM_SECRET=",
        )
        lines = []
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    if not any(line.startswith(p) for p in SKIP_PREFIXES):
                        lines.append(line)
        lines.append(f"OPENAI_API_KEY={key}\n")
        lines.append(f"OPENAI_BASE_URL={url}\n")
        lines.append(f"LAWCLAW_MODEL={model}\n")
        if feishu_app_id:
            lines.append(f"FEISHU_APP_ID={feishu_app_id}\n")
        if feishu_app_secret:
            lines.append(f"FEISHU_APP_SECRET={feishu_app_secret}\n")
        if wecom_corp_id:
            lines.append(f"WECOM_CORP_ID={wecom_corp_id}\n")
        if wecom_bot_id:
            lines.append(f"WECOM_BOT_ID={wecom_bot_id}\n")
        if wecom_secret:
            lines.append(f"WECOM_SECRET={wecom_secret}\n")
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # 同步保存律师画像到 backend/.hermes/USER.md（让 Memory 系统自动加载）
        profile = params.get("profile")
        if profile and isinstance(profile, dict):
            try:
                user_md_path = BACKEND_DIR / ".hermes" / "USER.md"
                user_lines = ["# 律师画像", ""]
                if profile.get("name"):
                    user_lines.append(f"- 姓名：{profile['name']}")
                if profile.get("firm"):
                    user_lines.append(f"- 律所：{profile['firm']}")
                if profile.get("title"):
                    user_lines.append(f"- 职位：{profile['title']}")
                if profile.get("practiceAreas"):
                    areas = profile["practiceAreas"] if isinstance(profile["practiceAreas"], list) else [profile["practiceAreas"]]
                    user_lines.append(f"- 执业领域：{'、'.join(areas)}")
                if profile.get("teamSize"):
                    ts_map = {"solo": "个人执业", "small": "2-10人", "medium": "11-50人", "large": "50人以上"}
                    user_lines.append(f"- 团队规模：{ts_map.get(profile['teamSize'], profile['teamSize'])}")
                if profile.get("yearsOfPractice") is not None:
                    user_lines.append(f"- 执业年限：{profile['yearsOfPractice']} 年")
                user_lines.append("")
                user_lines.append("## 个性化要求")
                user_lines.append("- 在法律分析中考虑该律师的执业领域偏好")
                user_lines.append("- 根据执业年限调整术语层次")
                with open(user_md_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(user_lines))
            except Exception as e:
                sys.stderr.write(f"[setup_save] USER.md write failed: {e}\n")
                sys.stderr.flush()

        return {"status": "saved"}
    else:
        raise ValueError(f"Unknown method: {method}")

class StdinServer:
    def __init__(self):
        self.output = sys.stdout

    def send(self, data: str):
        self.output.write(data + "\n")
        self.output.flush()

    def run(self):
        self.send(json.dumps({"event": "ready", "model": "agnes-2.0-flash", "ag_ui_version": "0.1"}))
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = None  # 畸形 JSON 时 except 分支仍可安全取 id
            try:
                req = json.loads(line)
                method = req.get("method", "")
                params = req.get("params", {})
                req_id = req.get("id")

                # Stdio chat：创建 EventEmitter（AG-UI 事件写到 stdout，每行一个 JSON）
                if method == "chat":
                    def _stdout_raw_send(evt):
                        try:
                            self.send(json.dumps({"event": "agui", "payload": evt}, ensure_ascii=False))
                        except Exception:
                            pass
                    # 旧格式兼容性回调（仍发送 type:'delta' 等；新前端忽略）
                    def _legacy_stream(delta_text):
                        if not delta_text: return
                        self.send(json.dumps({"type": "delta", "data": delta_text}, ensure_ascii=False))
                    def _legacy_tstart(name, args=None):
                        self.send(json.dumps({"type": "tool_start", "data": {"name": name, "args": args}}, ensure_ascii=False))
                    def _legacy_tend(name, result=None):
                        self.send(json.dumps({"type": "tool_complete", "data": {"name": name, "result": result}}, ensure_ascii=False))
                    def _legacy_think(t):
                        if not t: return
                        self.send(json.dumps({"type": "thinking", "data": t}, ensure_ascii=False))
                    params["event_emitter"] = EventEmitter(
                        raw_send_fn=_stdout_raw_send,
                        delta_compat_cb=_legacy_stream,
                        tool_start_compat_cb=_legacy_tstart,
                        tool_complete_compat_cb=_legacy_tend,
                        thinking_compat_cb=_legacy_think,
                        thread_id=params.get("thread_id"),
                    )

                result = handle_request(method, params)
                self.send(json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id}))
            except Exception as e:
                self.send(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": req.get("id") if isinstance(req, dict) else None}))

class WsServer:
    def __init__(self, host="127.0.0.1", port=9876):
        self.host = host
        self.port = port

    async def handler(self, websocket):
        loop = asyncio.get_running_loop()
        # LiveKit rtcSessionWorker 模式：每连接一个串行泵。
        # 同一连接上同时只允许一个 chat run（前端重复发送/多窗口共用连接时防并发跑双 agent）；
        # abort/ping/检索等控制与轻量请求不受锁限制，保证"停止"按钮始终可达。
        chat_lock = asyncio.Lock()

        # 发送 ready + 协议版本（前端据此判断是否支持 AG-UI）
        try:
            await websocket.send(json.dumps({
                "event": "ready",
                "model": "agnes-2.0-flash",
                "ag_ui_version": "0.2",   # 对齐官方 ag-ui 协议（RUN_ERROR/REASONING_*/threadId/timestamp）
            }))
        except Exception:
            pass

        async for raw in websocket:
            # 预置：畸形 JSON 时 except 分支仍可安全取 id，且 finally 不会误释放他人持有的锁
            req = None
            method = ""
            acquired_chat_lock = False
            try:
                req = json.loads(raw)
                method = req.get("method", "")
                params = req.get("params", {})
                req_id = req.get("id")

                # LiveKit 模式：chat 请求按连接串行化；已有 run 在跑则直接回忙错误
                if method == "chat" and chat_lock.locked():
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "error": {"code": -32002, "message": "当前会话正在处理上一条问题，请稍候或先点击「停止」"},
                        "id": req_id,
                    }, ensure_ascii=False))
                    # 注意：此处不得走 finally 的释放分支——锁是别的 run 持有的
                    req = None
                    method = ""
                    continue

                # Inject streaming callbacks for chat method
                # P0 更新：优先使用 EventEmitter（AG-UI 协议事件），同时双发旧的 {type:'delta'} 等事件
                if method == "chat":
                    def _ws_raw_send(evt):
                        """线程安全：把 AG-UI 事件从工作线程 push 回 async loop。"""
                        try:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send(json.dumps({
                                    "event": "agui",
                                    "payload": evt,
                                }, ensure_ascii=False)),
                                loop,
                            )
                        except Exception:
                            pass

                    # Legacy 兼容事件（旧 lib/backend.ts 消费）
                    def _ws_delta_legacy(delta_text):
                        if not delta_text: return
                        try:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send(json.dumps({"type": "delta", "data": delta_text})),
                                loop,
                            )
                        except Exception:
                            pass
                    def _ws_tstart_legacy(tool_name, args_preview=None):
                        try:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send(json.dumps({
                                    "type": "tool_start",
                                    "data": {"name": tool_name, "args": args_preview},
                                })),
                                loop,
                            )
                        except Exception:
                            pass
                    def _ws_tend_legacy(tool_name, result_preview=None):
                        try:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send(json.dumps({
                                    "type": "tool_complete",
                                    "data": {"name": tool_name, "result": result_preview},
                                })),
                                loop,
                            )
                        except Exception:
                            pass
                    def _ws_thinking_legacy(thinking_text):
                        if not thinking_text: return
                        try:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send(json.dumps({
                                    "type": "thinking",
                                    "data": thinking_text,
                                })),
                                loop,
                            )
                        except Exception:
                            pass

                    params["event_emitter"] = EventEmitter(
                        raw_send_fn=_ws_raw_send,
                        delta_compat_cb=_ws_delta_legacy,
                        tool_start_compat_cb=_ws_tstart_legacy,
                        tool_complete_compat_cb=_ws_tend_legacy,
                        thinking_compat_cb=_ws_thinking_legacy,
                        thread_id=params.get("thread_id"),
                    )

                if method == "chat":
                    await chat_lock.acquire()  # 串行泵：同一连接同时只跑一个 run
                    acquired_chat_lock = True
                result = await loop.run_in_executor(None, handle_request, method, params)
                await websocket.send(json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id}))
            except Exception as e:
                await websocket.send(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": req.get("id") if isinstance(req, dict) else None}))
            finally:
                # 只释放本次真正拿到的锁：否则忙错误分支（continue）会穿透到这里，
                # 把正在运行的 run 的锁提前放掉，破坏同连接串行化。
                if acquired_chat_lock and chat_lock.locked():
                    try:
                        chat_lock.release()
                    except RuntimeError:
                        pass

    def start(self):
        try:
            import websockets
            async def serve():
                async with websockets.serve(
                    self.handler, self.host, self.port,
                    ping_interval=None,  # disable keepalive pings (LLM calls can be slow)
                ):
                    await asyncio.Future()
            asyncio.run(serve())
        except Exception as e:
            sys.stderr.write(f"WS server failed: {e}\n")
            sys.stderr.flush()

def main():
    import sys as _sys
    # --ws mode: run only WebSocket server (for dev without Tauri stdin)
    if "--ws" in _sys.argv:
        ws = WsServer()
        print(f"[LawClaw] WebSocket server starting on ws://{ws.host}:{ws.port}", file=_sys.stderr)
        _sys.stderr.flush()
        ws.start()
        return
    ws = WsServer()
    t = threading.Thread(target=ws.start, daemon=True)
    t.start()
    stdio = StdinServer()
    stdio.run()

if __name__ == "__main__":
    main()
