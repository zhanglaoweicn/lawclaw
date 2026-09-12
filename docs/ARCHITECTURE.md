# LawClaw 律爪 — 架构地图

给准备研究本项目的读者：这份文档说明**代码分布与数据流向**，读完能知道改哪一层。
业务细节与决策记录见根目录 `AGENTS.md`（那是本项目的过程日志，信息量最大）。

## 一句话

面向中国执业律师的桌面 AI 智能体：Tauri 壳 + Vue 3 前端 + Python 后端（JSON-RPC），
后端复用 Hermes-agent 作为 agent 运行时，叠加法律工具、法律技能库与法律数据源。

## 分层

```
┌─────────────────────────────────────────────────────────────┐
│ src-tauri/            Tauri（Rust）桌面壳                     │
│   src/lib.rs          启停后端进程、窗口生命周期、后端目录解析  │
├─────────────────────────────────────────────────────────────┤
│ src/                  Vue 3 + Element Plus 前端（无 vue-router）│
│   App.vue             视图切换编排（currentView 状态机）        │
│   components/         工作台/助理/案件/日程/文件/技能/专家/配置  │
│   stores/             Pinia：matter/chat/schedule/file/timeline │
│                        /expert/skill/setup/theme/caseView      │
│   lib/backend.ts      WebSocket(ws://127.0.0.1:9876) JSON-RPC  │
│   lib/db.ts           IndexedDB（文件/时间轴）                  │
│   seed/               演示数据种子                              │
├─────────────────────────────────────────────────────────────┤
│ backend/              LawClaw 自建后端（本项目的核心增量）      │
│   main.py             双协议 JSON-RPC 入口（stdio + WS 9876）  │
│   citations.py        法条引用抽取（纯函数）                    │
│   doc_review.py       文书细节校对引擎 M1–M8 + 法条时效         │
│   npc_law.py          国家法律法规数据库客户端（官方时效主源）    │
│   doc_intel.py        文档抽取适配层 + 案件知识库(BM25) + 经验召回│
│   watchdog.py         值守助手（案件扫描 + cron 晨报）          │
│   config.yaml         技能启用白名单、MCP 服务器、品牌           │
│   .hermes/skills/     法律技能库（Apache-2.0，见 NOTICES）      │
├─────────────────────────────────────────────────────────────┤
│ 根目录 *.py / agent/  Hermes-agent 底座（MIT，独立维护的 fork）  │
│   run_agent.py        AIAgent 类（agent 循环、工具调度）        │
│   tools/ registry/   工具注册表（含 MCP 工具发现）              │
│   providers/          LLM provider 适配                        │
│   cron/ gateway/      定时任务 / IM 网关                       │
└─────────────────────────────────────────────────────────────┘
```

## 关键数据流

**一次对话**

```
ChatPanel → backend.ts (WS)
  → main.py handle_chat()
  → 组装系统提示词：律师画像 + 技能(SKILL.md) + 案件上下文
              + 案件文档库检索(kb_search) + 历史经验召回(experience_search)
  → run_agent.AIAgent 跑 agent 循环（可调用工具：检索/读文件/终端/MCP…）
  → 流式回传 AG-UI 事件（RUN_STARTED / TEXT_MESSAGE_CONTENT / TOOL_CALL_* …）
  → extract_citations() 抽引用 → 前端 CitationCard 逐条 verify_citation 验证
```

**一次文书校对**

```
FilePanel 预览 → backend review_document
  → doc_review M1–M8 机械规则（模板残留/称呼/条号格式/金额/术语/日期/交叉引用/全角）
  → CIT 维度：extract_citations → npc_law 查官方时效（限流节流 + 本地废止表兜底）
  → 返回 issues[{module,severity,message,suggestion,line,excerpt}] + stats
```

**法律数据源**（三层，逐级降级）

| 用途 | 主源 | 兜底 |
|---|---|---|
| 法规/案例检索 | 元典开放平台 MCP（6 个 SSE 服务器） | 元典 HTTP API |
| 法条时效性 | NPC 国家法律法规数据库（免费、权威） | 本地 `DEPRECATED_LAWS` 表 → 元典 |
| 文书细节 | 本地规则引擎（无外部依赖） | — |

## 值得研究的设计点

1. **引用可信度**：`backend/citations.py` 的抽取窗口「不跨句、不跨法名」——跨法名会把裸条号挂错法名，产出杜撰式引用（比没有卡片更危险）。
2. **双时间线期限模型**（借鉴 semantica 的 BiTemporalFact）：`DeadlineItem` 带 `validFrom` / `supersededAt` / `history[]`，改期限本身成为可回溯的审计记录，而非覆盖。
3. **决策即一等公民**：案件决策以 `type:'decision'` 写入时间轴并保留结构化 metadata，作为未来"同类案件检索"的语料。
4. **上下文透明化**：每次回复返回 `context_stats`（历史轮数/文档片段/经验条数/附件数），前端显式展示，避免"模型到底看到了什么"黑箱。
5. **双风味构建**：同一套代码产出「演示版（含虚构数据）/ 客户版（空台账、无密钥）」两种交付物，安装标识分离使两者互不污染（见 `scripts/build_release.py`）。
6. **发行物自检与冒烟**：打包流程末尾会用包内捆绑运行时**真实启动一次后端**并打 RPC，拦"漏带模块/漏带技能"这类静态检查抓不到的问题。

## 本地跑起来

见 `README.md` 的「开发」与「本地构建桌面端应用」两节。

## 许可

本仓库 MIT；内嵌法律技能内容来自 Anthropic `claude-for-legal`（Apache-2.0），
署名与修改声明见 `THIRD_PARTY_NOTICES.md`。
