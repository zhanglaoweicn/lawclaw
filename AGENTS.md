## Goal
- Build LawClaw (律爪), a vertical AI agent for Chinese lawyers, forked from Hermes-agent, delivered as a Tauri desktop app with Vue 3 + Element Plus frontend.

## Constraints & Preferences
- Frontend: Vue 3 + Element Plus (preferred over React/shadcn)
- Backend: Fork Hermes-agent for independent maintenance (not submodule/pip dependency)
- Desktop: Tauri (not Electron) for minimal bundle size
- LLM API: `https://api.deepseek.com/v1`（OpenAI 兼容协议；亦可换任意兼容端点）, model `deepseek-flash`, key 由用户在首启向导/「配置」页填写（**不入库、不写文档**，见 `backend/.env`）
- Legal data: **元典开放平台** MCP (law/case/company SSE servers) + HTTP API fallback
- Paid upgrade path: 北大法宝 MCP (future)
- Simple startup flow – first-launch wizard for API key + practice profile
- Lawyer-specific dashboard – replace Hermes generic GUI with legal workbench (案件管理, 快捷操作, 数据统计)
- Dev/test phase – localStorage for persistence, no database yet
- HERMES_HOME isolated to `backend/.hermes/` – separate from user's `~/.hermes/`

## Progress
### Done
- Created `LawClaw/` project root under hermes-agent-main
- Initialized Tauri + Vue 3 + TS skeleton (`src-tauri/`, `src/`)
- Installed Element Plus + icons + Tauri shell + Pinia + marked + @vueuse
- Copied Hermes-agent source (agent/, hermes_cli/, tools/, gateway/, plugins/, providers/, skills/, cron/) into LawClaw
- Created `backend/main.py` — dual-protocol JSON-RPC server: stdin/stdout + WebSocket port 9876
- Created `backend/.env` — API key for Agnes, loaded with UTF-8 encoding
- Configured Tauri: `tauri.conf.json` (window 1280x800, sidecar, shell plugin)
- End-to-end verified: backend responds in Chinese over WebSocket and stdin/stdout
- Phase 1 "对话界面完善": SessionList, ChatPanel, CitationCard, Pinia stores, backend.ts client, types/legal.ts
- Phase 2 "律师工作台": LawyerDashboard, SetupWizard, MatterList, MatterStore, SetupStore, App.vue orchestration
- **Legal SKILL.md files created**: 4 skills under `skills/legal/` (contract-review, legal-research, fee-calculator, document-draft)
- **Skills deployed**: copied to `skills/legal/` and `backend/.hermes/skills/legal/` for agent discovery
- **Regex bug fixed**: `extract_citations()` missing closing `)` in capturing group → `unterminated subpattern` error resolved
- **WebSocket threading fixed**: `WsServer.handler` now runs `handle_request` in `loop.run_in_executor(None, …)` to avoid blocking async event loop during LLM calls
- **WebSocket keepalive**: `ping_interval=None` prevents timeout drops during long agent.chat() calls (>20s)
- **Citation extraction improved**: article number now parsed from raw text with `re.search(r'第…[条款项]', …)` to handle `》第584条` style prefixes
- **config.yaml updated**: `document-draft` skill added to `skills.enabled`
- **SetupWizard → backend wired**: on finish, calls `setup_save` RPC to persist API key/base_url/model to `backend/.env`
- **ChatPanel → setupStore wired**: `sendMessage()` passes `setupStore.apiKey/baseUrl/model` per RPC
- **pnpm build**: compiles clean (vue-tsc --noEmit, vite build)
- **NPC API deprecated**: discovered `https://flk.npc.gov.cn/api/` returns SPA HTML since Aug 2025 Phase II redesign
- **Migrated legal search to 元典**: rewrote `handle_legal_search()` in `backend/main.py` and `tools/legal_search.py` to `POST https://open.chineselaw.com/open/rh_fg_search` with `X-API-Key` header
- **Found 6 professional legal skill packs** (元力工场, 69 skills total) under `D:\Down\toolkits_legal-skillpack-*`
- **Analyzed all 6 packs**: bundle.json → SKILL.md (YAML frontmatter) → profiles/ → connectors/ → workflows/ format. install.py auto-detects 8 agent frameworks. Primary data source: 元典 MCP
- **Installed 4 packs** (48 skills) into `backend/.hermes/skills/`:
  - `litigation-legal` (19 skills: matter-intake, evidence-review, demand-draft, brief-drafter, chronology, claim-chart, subpoena, deposition, etc.)
  - `legal-research-cn` (4 skills: law-search, case-search, deep-research, company-search)
  - `corporate-legal` (13 skills: entity-compliance, diligence, board-minutes, closing-checklist, etc.)
  - `commercial-legal` (12 skills: review, NDA, SaaS-MSA, vendor-agreement, amendment-history, etc.)
- **Enabled key skills in config.yaml** (28 skills, curated selection)
- **Verified 52 skills discovered** by Hermes agent (48 pro + 4 basic)
- **Configured 元典 MCP servers** in config.yaml (3 SSE servers: law/case/company)
- **Fixed Hermes MCP bug**: `_run_http()` at `tools/mcp_tool.py:1432` checked only `_MCP_HTTP_AVAILABLE` (old API `streamablehttp_client`) but not `_MCP_NEW_HTTP` (new API `streamable_http_client`). MCP SDK v1.28.1 only has the new API. Fixed to `if not (_MCP_HTTP_AVAILABLE or _MCP_NEW_HTTP):`
- **Fixed sampling protocol mismatch**: 元典 Java server rejects MCP SDK v1.28.1's `SamplingCapability.tools` field. Disabled sampling (`sampling: {enabled: false}`) for all 元典 servers
- **MCP tools auto-discovered at startup**: added `discover_mcp_tools()` call in `backend/main.py`
- **Final verification**: 3 MCP servers → 53 tools, 52 skills, 125 total tools in registry, legal search returns 10 results, agent initializes

### In Progress
- *(none — all integration tasks verified)*

### Blocked
- *(none)*

### Done (调研吸收⑤ — 值守助手上线: Hermes cron 定时监控本地化, Sep 12)
- **基础设施复用**：发现 Hermes 上游自带完整 cron 调度器（cron/jobs+scheduler，支持 "30 8 * * 1-5" 表达式/script 数据预采集/no_agent 纯脚本任务/3 分钟硬中断/tick lock），且 `_start_desktop_cron_ticker`（hermes_cli/web_server.py）专为非 gateway 桌面后端设计——LawClaw main.py 直接复用（HERMES_DESKTOP=1，interval 300s，daemon 线程，失败不阻塞）
- **新增 backend/watchdog.py + RPC 四个**：`watchdog_sync`（前端推送案件摘要落盘 .hermes/data/watchdog_matters.json——案件数据在前端 localStorage，后端 cron 扫描靠此同步）/ `watchdog_status`（即时扫描：逾期期限/7日内临期/7日内开庭/待处理·证据收集超14天停滞）/ `watchdog_briefing`（最近晨报，读 cron/output/<job_id>/*.md）/ `watchdog_run_now`（trigger_job 立即触发）
- **cron jobs**：lawclaw-morning-briefing（工作日 08:30）+ lawclaw-weekly-review（周日 20:00），**no_agent=True 模式**（扫描脚本 stdout 即交付——cron 会话的 LLM provider 凭证解析在 LawClaw 自建后端不可靠：provider 注册表无 'openai'→改 'custom' 后 key 又走 profile secret scope（.hermes/.env）→ 401 no-key-required；**修复**：watchdog.sync_profile_env() 把 backend/.env 同步到 .hermes/.env，但 v1 晨报仍取 no_agent 纯扫描以保可靠；AI 分析由前端按钮经普通 chat 链路按需生成）
- **扫描脚本**：`backend/.hermes/scripts/watchdog_scan.py`（create_job 的 script 参数是**文件路径**而非源码——踩坑）；输出中文告警清单
- **前端**：Dashboard 新增值守卡片（最近扫描时间/在册案件/告警列表按逾期-开庭-临期-停滞分级着色/「生成 AI 晨报」按钮走 chat RPC 生成 400 字行动建议）；冷启动 WS 竞态重试一次
- **实证**：E2E 全通——sync 13 案→status 7 告警（真实数据）→trigger→output 目录落盘→briefing 渲染；AI 晨报按钮走 chat 生成；audit 12/12
- **调试教训**：①heredoc 写含 
 转义的代码会折叠成真换行——用 Read/Edit 工具或 chr(92)；②executions 表无正文，no_agent 输出在 cron/output/<job_id>/*.md；③backend/.env 与 backend/.hermes/.env 是两套凭证源，cron 会话读后者
### Done (调研吸收④ — claude-for-legal-ZH 增量领域插件引入 55 技能, Sep 11)
- **调研对象**：github.com/zhou210712/claude-for-legal-ZH（Anthropic 官方 claude-for-legal 的中国法系统性本地化，海泰陈石律师，212 stars，**Apache 2.0 可商用**；150 技能/12 领域/588 文件；litigation/commercial/corporate 与元力工场包同名同源零增量）
- **引入 6 个增量领域插件 55 技能**（新安装脚本 `scripts/install_cfl_skills.py`，幂等可重放）：
  - employment-legal 全 18（劳动法：解除审查/劳动关系认定/工时答疑/规章制度/内部调查系列/假期追踪/手册更新/跨国用工）
  - ip-legal 10（警告函/清查/FTO/侵权分诊/交底/IP条款/开源合规/组合/下架）
  - ai-governance-legal 8（AI清单/算法影响评估/政策监控起草/监管缺口/场景分诊/供应商AI审查）
  - privacy-legal 7（DPA审查/DSAR响应/个保法影响评估/政策监控/缺口分析）
  - regulatory-legal 7（征求意见/要求浮现/缺口梳理/政策对比改写/动态追踪）
  - product-legal 5（功能风险评估/问题快判/上线审查/宣传合规）
  - 各插件 customize/matter-workspace 跳过（与 LawClaw 原生体系重叠）
- **安装适配**（install_cfl_skills.py）：目录与 frontmatter name 前缀化（employment-termination-review，防跨插件同名撞 id——skill id 取 frontmatter name）；SKILL.md 内 `~/.claude/plugins/config/...` 路径改写为技能目录绝对路径；插件根 CLAUDE.md（实务画像模板）+ references/（中国法核心规则，如 labor-core-rules 710 行）随附每个技能目录
- **引导流设计**：领域技能依赖 CLAUDE.md 画像（未初始化时会主动提示先跑初始化访谈）——6 个 cold-start-interview 已随装，形成"访谈建档→技能深度工作"闭环；与 LawClaw SetupWizard 画像互补（插件画像管审查指引/风险标记/输出格式）
- **config**：启用 27→82，两份同步；GROUP_MAP 扩展 6 组（劳动人事/知识产权/AI 治理/数据隐私/监管合规/产品合规）；SKILL_DISPLAY_NAMES +55 中文名
- **实证**：list_hermes_skills=82（分组正确）；**employment-termination-review 真实 LLM 端到端**——8063 字解除审查报告，agent 自行读取技能文件并调用元典 MCP 做法条逐条校验，输出挂保密标头；audit 12/12；技能页 100 卡 16 分组
- **未引入**：legal-clinic(16)/law-student(13)/legal-builder-hub(10)（产品定位待定：诊所/法学生/技能构建者）；agents/ 定时监控蓝图（renewal-watcher 等）待结合 Hermes cron 立项
### Done (调研吸收③ — 文书细节校对引擎 M1-M8 + 法条时效, Sep 11)
- **新增 `backend/doc_review.py`**（纯函数模块）：借鉴 legal-tools 文书细节校对 Skill 的 M1-M8 维度划分（MIT），面向纯文本文书自研实现——M1 模板残留/ M2 称呼一致/ M3 法条格式（简称首用全称 + 条号汉字规范，映射表 12 部法律）/ M4 金额一致（中文大写→数值比对）/ M5 术语误用（订金定金之辨/权力义务/签定）/ M6 日期逻辑（起止倒置+不存在日）/ M7 交叉引用（本合同第X条未定义）/ M8 全角数字；**CIT 法条时效**：extract_citations + NPC 官方时效（限流保护最多查 8 部）+ 本地废止表——「起草→校对→导出」闭环成形
- **RPC**：`review_document` {text, check_citations} → issues[{module,severity,message,suggestion,line,excerpt}] + stats；**前端**：FilePanel 预览头部「校对」按钮 + 右键菜单「校对文书」（md/txt）→ 校对报告对话框（严重/一般/提示分级 + 分行定位 + 建议 + 复制报告）
- **调试实录**：_M3_ABBR 漏"合同法"条目（静默漏报）；M7 正则少捕获组；m7/num_to_cn 迁 citations.py 供 main 与 doc_review 共用；测试数据两处设计修正（甲方已定义不算 M2 违规；"某某律所"本就该被判占位符——严重级正确）
- **实证**：test_doc_review.py 14/14（瑕疵文书 9 维全命中 + 干净文书零严重 + 空文本）；GUI 校对 AI 生成的催告函 → 26 项一般问题（阿拉伯条号/简称引用，全部真实命中）；audit 12/12
- **调研吸收全部完成**：P1 verify 双源（de02c74）→ P2 深度检索+官方原文（8f568c6）→ P3 文书校对（本次）；人民法院案例库定位为用户自备账号可选源（暂不集成）
### Done (调研吸收② — 元典 MCP 深度检索: 权威案例 + 法条反查类案 + 官方原文, Sep 11)
- **关键更正**：MCP 工具注册名是**双下划线** `mcp__yuandian_case__yuandian_rh_qwal_search`（mcp__{server}__{tool}，73 个工具含元工具）——此前记载的单下划线命名有误；HTTP open API 对 qwal/ptal/ft_detail **全部静默空返回**（只支持 rh_fg_search），深度检索必须走 MCP。调用入口：`tools.registry.registry.dispatch(name, args)`（内部经 MCP loop + 重试护栏），RPC 上下文可直接用
- **新增 RPC**：`legal_search_authoritative`（权威案例：rh_qwal_search，qw 全文关键词 + source 来源数组【指导性/公报/参考/典型案例】，返回官方要旨）；`legal_search_by_law`（法条反查：rh_ptal_search 的 **yyft 援引法条反查**，格式=「全称+中文数字条号」数组）；`npc_law_docx_url`（NPC 官方 DOCX 签名 URL 两步获取，约 1h 有效）
- **工具函数**：`_num_to_cn`（立法技术规范口径：组合语境 10-19 写「一十X」如 917→九百一十七条；独立条号 10→十、17→十七）；`_parse_law_query`（"民法典 第917条"→全称+中文条号）
- **解析口径**：qwal/ptal 返回 `data.lst`（非 list/rows），条目字段 fbdw/cprq/llm_content（案号##裁判要点+案情）；HTTP 静默空返回（200 但 0 条）是元典通病，MCP 路径同样要校验 message
- **前端**：LegalSkill 增 searchType 字段（law/case/authoritative/case-by-law 泛化，替代 id 硬编码）；skill.ts 新增「权威案例」「法条反查」两个 RPC 内置技能（45 卡）；CitationCard 增「官方原文」按钮（NPC 验证成功且带 bbbs → npc_law_docx_url → 打开官方 DOCX）；RPC 结果格式化增案号与 160 字要旨摘要行
- **实证**：权威案例 4 条（保管合同，最高法发布）；法条反查民法典917条→**349 条判例**、刑法263条→13.9 万条；GUI 检索结果带案号+要旨；audit 12/12
- **注意**：handle_legal_search 的 search_type 派发要与前端新通道同步（本轮踩坑：新 search_type 落入默认 law 分支）
### Done (调研吸收 legal-tools — verify_citation 双源升级, Sep 11)
- **调研对象**：github.com/moyupeng0422/legal-tools（华诚所律师维护，四块：NPC 法规库 MCP / 人民法院案例库 MCP / 元典实务指南（130+ 次调用）/ 文书校对 Skill M1-M8）
- **P1 落地——verify_citation 双源升级**：新增 `backend/npc_law.py`（国家法律法规数据库 flk.npc.gov.cn 二期 API 自研客户端，未复制第三方代码）
  - 关键发现：基础 search/list 的分词相关度排序不可控（搜"合同法"返回无关法律）——**正确路径是高级检索 highSearch/highSearch（title 字段条件，fieldName/searchType/index/orderByParam 结构）**，"合同法" total=5 即含本体
  - 请求体必须含全部字段（空数组也要）；限流对策：请求间隔 0.5s + 1s/2s/4s 递增重试（实测偶发 15s 读超时）+ 24h TTL 缓存
  - **时效性官方直给**：sxx 3=有效/2=已修改/1=废止/4=未生效——verify 改为 NPC 主源（免费+权威+覆盖全部废止法）+ 本地 DEPRECATED_LAWS 优先 + 元典兜底的三层结构
  - 实证：民法典/城市房地产管理法→NPC 现行有效；民法通则/民法总则（本地表外）→NPC 正确判废——废止覆盖从本地 12 部扩展到全库；audit 12/12；GUI 真实对话 20 张引用卡全绿
- **后续待做**（调研剩余项）：P2 元典集成升级（ft_detail 省费/权威案例通道/法条反查/静默错误加固）、P2 引用卡官方原文下载（flk DOCX 管线）、P3 文书校对技能（MIT 引入 M1-M8）、人民法院案例库定位为用户自备账号可选源
### Done (律师角色全业务链 GUI 实测 — 9 阶段无死角走查, Sep 11)
- **方法**：扮演独立执业民商事律师，用自洽模拟案情（恒信贸易 v 宏达建设借款 350 万 → 仓储纠纷 62 万）完整走业务生命周期；自动化与组件级驱动结合（EP Select 下拉在本环境不稳定处改 dev setupState 直驱，业务验证点在提交后的数据流与 RPC）
- **①接案**：正常建案✓（跳详情）；**利益冲突拦截✓**（对方当事人当委托人→规则1+2 双向 blocked、按钮禁用、《律师法》第39条）；**同客户第二案✓**（P1-A 修复实证：无冲突正常创建）
- **②案件管理**：阶段流转（待处理→审查中）✓；**期限智能计算✓**（答辩期15日→届满逢中秋自动顺延至9-28，附《民法典》第201条）；**编辑留痕✓**（变更原因入修订历史）；**撤销→恢复✓**（软删除双时间线：revs=2=编辑+撤销记录，设计正确）；记录决策✓；推荐技能随阶段变化✓；添加到日历✓（ensureCourtItem 规范键）
- **③日程**：matter 同步项在✓；**发现并修复 date-only 开庭冲突漏报**（存 UTC 零点→检测窗口错开）——normalizeCourtDateTime 统一本地 09:00 + 同日即冲突判定，复验命中✓；开庭准备模板✓；完成 toggle✓；.ics 导出下载✓
- **④AI协作**：关联案件对话✓；30 步工作流产出催告函提纲 2418 字——标的额/案号/开庭日/原告立场校准词汇全部来自案件+访谈画像联动，经验召回 3 条；保存为案件文书✓（IndexedDB+上传即解析 2718 字）；导出 Word✓（export_docx RPC）；**中文编辑闭环✓**（P1-B：解码→批注→保存→重解码无乱码）
- **⑤检索**：法条速查 10 条带时效标注✓（链路通，长自然语 query 召回相关性一般——记录为检索调优项）；类案检索 case 通道✓
- **⑥专家**：召唤→保密标头回复 2559 字（第917条过错责任分析，访谈画像联动）✓
- **⑦时效计算器**：2023-09-11 起算→今天恰好届满（-1天已过期+第188条依据）、2024-06-01→剩262天✓
- **⑧会话/搜索**：重命名/删除✓；全局搜索"仓储"命中案件+会话组✓（文件组仅搜名称不搜全文——记录为改进项）
- **⑨持久化**：reload 后 13 案件/重命名会话/48 日程项/文书文件全部保留✓
- **待修发现**：无新增 P0/P1；观察项 2（检索相关性调优、全局搜索文件含全文）记录待排期
### Done (GUI 实测轮 — 引用验证修复 + 剪贴板降级, Sep 11)
- **实测A（引用）**：真实对话产出 11 条引用（含废止红卡/多条款级/数字与中文条号）——复制按钮、块级"复制全部"、废止标注全部工作。**发现并修复 verify_citation 大面积"未找到"**：keyword 把条号拼进法规名搜索（"民法典 第585条"）被元典全文检索稀释、召回不相关文件；且有效性本是法规级属性。修复：keyword 剥离条号只用法规名、候选按规范化名称最短贴近匹配（防"民法典"误命中含该简称的司法解释）、pageSize 3→10、补 Accept 头。复测：民法典条级/款级 ✅现行有效、合同法 ❌已废止（本地库）、简称"合同法司法解释（二）"保持诚实"未找到"
- **实测A发现剪贴板 NotAllowedError**：navigator.clipboard 在文档失焦（合成点击/WebView 策略）下抛 "Document is not focused"。新增 `src/lib/clipboard.ts` copyText（Clipboard API → 隐藏 textarea execCommand 降级），替换 ChatPanel/CitationCard/SkillPage 4 处调用。真实点击实测"已复制 5 条引用"
- **实测B（冷启动访谈全链路）**：技能页"诉讼业务初始化访谈"→使用此技能→对话启动——agent 经 skill_view/search_files/terminal 全程工具调用成功（19-20 步 run），返回访谈 Part 0 三问（使用者/角色/立场），且读取到前端 SetupWizard 已有画像做预填（跨系统联动生效）；回答一轮后正确锁定路径（保密标头/独立执业路径/原告校准词汇）并进入集成检查——**多轮交互闭环 + 工具层修复双重实证**
- **顺带发现**：后端重启后前端 skillStore 缓存不刷新（backendSkillsLoaded 一次失败/已加载即永久跳过）——需 reload 才能看到新技能列表，已在评审遗留项中记录
- **回归**：audit 12/12、vue-tsc 零错误、vite build 通过
### Done (技能库整合 + 冷启动访谈接线 + P0 工具层修复, Sep 11)
- **路线图 #2 基础技能去重**：下线 `legal/contract-review`、`legal/legal-research`（与专业包 commercial-review / prc-legal-research-law-search 重复）——从两份 config.yaml enabled 移除 + 删除 backend/.hermes/skills/legal/ 部署目录（根 skills/legal/ 存档保留）；`legal/fee-calculator`、`legal/document-draft` 保留（无包等价物，工作台快捷卡仍映射）。前端快捷卡早已映射专业包 id，无破坏
- **路线图 #4 冷启动访谈接线**：启用 3 个技能包冷启动访谈（litigation/corporate/commercial-cold-start-interview，配置计数 26→27），SKILL_DISPLAY_NAMES 补中文（诉讼/公司/合同业务初始化访谈）；环境变量 LEGAL_AGENT_PROFILE_HOME（backend/.hermes/profiles）此前已接线，访谈把执业画像写入 profile.md 供下游包技能读取。端到端实证：chat(skill_id) 正常进入访谈 Part 0（使用者/角色/立场分流）
- **P0 发现与修复——agent 工具层在 Python 3.14 下全线瘫痪**：冷启动访谈 e2e 暴露 `DaemonThreadPoolExecutor 没有 _initializer` ——3.14 重构了 ThreadPoolExecutor 内部（`_initializer/_initargs` → `_create_worker_context` WorkerContext；`_worker` 4参→3参）。`tools/daemon_pool.py:_adjust_thread_count` 镜像的是 3.8–3.13 私有结构 → 所有工具调用（read_file/terminal/skill_view…）进入实现前即炸。**此前未暴露的原因**：纯对话与 RPC 直连（legal_search 等）不走工具层，audit 的 chat 用例恰好无工具调用。修复：`_adjust_thread_count` 按 `_create_worker_context` 属性分派新旧两代 spawn 签名（3.14 走官方 WorkerContext 路径，≤3.13 走原镜像）。修复后访谈正常 + audit 12/12
- **路线图 #3 阻塞**：ip-legal / ai-governance 两包源（原 D:\Down	oolkits_legal-skillpack-*）已被清理，无法安装（21 技能）——待用户提供包源后按既有流程接入
- **教训**：audit 的 chat 用例未覆盖工具调用路径——"12/12 通过"不等于工具层健康；后续回归应加一条"强制工具调用"用例（如让 agent 读一个文件）
- **回归**：citations 单测 12/12、audit 12/12（修复后复跑）、冷启动访谈 e2e 通过；后端重启加载新配置与修复
### Done (功能迭代 — 引用可信度 2.0, Sep 11)
- **定位**：路线图 Next Steps #5「引用展示打磨」——律师产品核心卖点（法条引用可信度）；后端 verify_citation RPC（元典法条有效性校验）已就绪，本轮补齐抽取广度与复制链路
- **抽取器重构**：`backend/main.py` 的 extract_citations + DEPRECATED_LAWS 迁出为纯函数模块 **`backend/citations.py`**（零副作用可单测，main.py 改 import，行为向后兼容）。抽取能力增强：
  - 多条并列："《民法典》第584条、第585条" → 每条一个引用（旧实现非贪婪只取第一条）
  - 款项级：第585条第2款（条后可选 款/项 后缀）
  - 通用书名号法名：《…法/解释/条例/规定/办法/意见/细则/修正案（一）》——覆盖司法解释/行政法规（如"最高人民法院关于适用〈民法典〉婚姻家庭编的解释（一）"），不再受白名单限制；裸法名白名单保留（跳过书名号已覆盖区域）
  - 按（法名,条号）去重（旧按全文去重，同条不同表述会出两张卡）；引用窗口不跨句（防下一句"第N条"误挂）；中文数字/区间端点/编章跳过
- **单测**：新增 `backend/tests/test_citations.py`（12 用例：并列/款项/司法解释/裸名/废止/去重/跨句/中文数字/区间/混合/编章/空文本）——12/12 通过
- **前端**：CitationCard 增"复制"按钮（复制抽取原文片段，可直接粘贴进文书）；ChatPanel 引用块标题改"引用来源（N条）"+ 增"复制全部"（逐条一行拼接）；已有的单卡自动验证（元典 verify_citation）与废止红卡不动
- **注意**：GUI 实测被用户占用浏览器窗口打断（用户当时在配置 DeepSeek），自动化让位；核心逻辑已由单测+build 覆盖，引用卡片人工冒烟见下
- **人工冒烟指引**：对话问"民法典违约金调整的规定（引第584/585条）"→ 引用来源（≥2条）→ 单卡"复制"/块级"复制全部"→ 状态徽章"✅现行有效"（元典自动验证）
- **回归**：citations 单测 12/12、vue-tsc 零错误、vite build 通过；后端已重启加载新模块（runtime python --ws）
### Done (全页面深度评审修复 — 工作台+侧栏 8 页, Sep 11)
- **评审方法**：前端 14k 行全量代码审查 + localhost:1420 GUI 实测逐页走查（首启向导/工作台/助理/技能/专家/日程/案件列表+详情/文件/配置），问题分级 P1×2/P2×8/P3 若干，随后分两轮全部修复
- **P1-A 利益冲突规则误伤**：`matter.ts checkConflict` 删除规则 3（"新案件委托人=现有案件委托人"曾返回 blocked 且建案按钮 disabled——同客户多案是正常代理，真正对立场景已由规则 1/2 覆盖）；`caseConstants.ts` ConflictType 同步移除
- **P1-B 中文编码缺陷**：新建 `src/lib/encoding.ts`（dataUrlToText/textToDataUrl，TextDecoder/Encoder），替换 useFileEditor（文件页+案件详情共用）与 ChatPanel 的裸 atob/btoa——中文 .md/.txt 预览乱码、btoa 抛 RangeError、保存写坏数据三个问题一并解决
- **助理页**：Enter 发送检查 `isComposing`（IME 选词回车不再误发）；技能 prompt 模板预填输入框（原先为死代码，实证"法律意见书"模板入框）；流式自动滚动（发送/挂载/watch(messages,deep) 贴底，用户上翻暂停）
- **专家页**：召唤改为 `setPendingPrefill`（预填不自动发送，实证 0 消息）；对话内 pickExpert 直接填 inputText（消除 pendingPrompt 滞后误发隐患）
- **双期限模型统一（数据一致性核心）**：编辑案件对话框"截止日期"从最近非开庭期限预填、保存走 updateDeadline（带修订留痕，实证"修订 1"徽章）或 addDeadline，不再写 legacy `deadline` 字段；CaseListView 截止排序用 getNearestDeadline；`schedule.syncFromMatters` 重写为按 `dl-{id}` 同步 deadlines[]（legacy `deadline-` 项清除），CalendarPage 深度监听 matters（期限编辑即同步）
- **工作台**：紧急期限 key 改用期限 id（修复同案多期限重复 key）、显示全部不再 slice(0,5)（实证 19 条计数=行数）、天数按自然日计算；"开庭倒计时"今天/明天边界修正
- **日程**："添加到日历"改 `ensureCourtItem` 按 court-{id} 规范键 upsert（消除重复开庭日程）；单条删除加确认
- **文件页**：全局视图分类芯片只显示默认分类+实际有文件的分类（实证 23→2，防无限膨胀）；拖拽上传提示改"已加入上传队列"
- **经验召回**：`timeline.loadAllEvents` 独立 allLoaded 标记（原 loaded+非空判断会被单案视图覆盖后永久跳过全量加载）
- **安全**：新增 `src/lib/markdown.ts`（marked+DOMPurify，新增依赖 dompurify@3.4），ChatPanel/CaseDetailView/FilePanel/SkillPage 四处 v-html 统一走消毒出口；GlobalSearch 高亮补 escapeHtml
- **切会话流式缓冲**：chat store 新增 runningSessionId + sessionBuffers——run 期间切走会话输出继续写入缓冲、切回恢复、完成落盘（GUI 实证：切走→切回，386 字回复完整）；typing 行按运行会话门控不串场
- **技能页**：内置直查技能改名消除同名（法规检索→法条速查、类案检索→案例速查、诉讼费计算→诉讼费速算，id 不变）；自定义技能补删除按钮（removeCustomSkill 原先无 UI 调用方）
- **清扫**：删除死组件 SettingsPanel.vue（App.vue showSettings 接线一并移除）、删除错误预设"Anthropic (via OpenAI)"、messageCount 文案统一"轮对话"（4 处）、formatDeadline >30 天改"剩/天后"（期限行日期不再显示两遍）、chat.ts totalSteps/showTemplateMenu/recentlyUsed/trl-send/重复 CSS 等死代码
- **回归**：vue-tsc 零错误、vite build 通过、四套后端测试不涉及（纯前端改动）；关键路径 GUI 实证（冲突/编码/IME 门控/技能模板/专家预填/日程同步/日历去重/分类收敛/切会话缓冲/技能删除）
- **待用户决策**：首启种子含"【测试用】多期限综合案件"（此前特意加的验证基准），是否对正式版隐藏待定
### Done (配置页布局重构 + 侧栏纯导航, Sep 11)
- **配置页布局重构**（用户反馈"菜单底色宽度溢出"）：根因 = `.settings-view-wrapper` 横向 flex 中 `.settings-view` 无宽度约束（内容宽 458px，右侧 800px 空白）。修复：`.settings-view { flex:1; min-width:0 }` 铺满；sv-body 改 flex 双栏；左菜单固定 176px + 药丸选中态（去 EP 竖线/active-bar）；内容区 `flex:1` 铺满 + tab-pane max-width 720px
- **侧栏纯导航**：MatterList 快捷列表从侧栏整体移除（用户两轮反馈冗余；案件切换保留案件页/Ctrl+K/顶栏面包屑三条路径），App.vue 清理 MatterList 引用与 showMatterList
- 注意：`viewHasInternalScroll` 的 cases 分支是滚动布局逻辑，与 MatterList 无关，勿混淆

### Done (元典 MCP 扩容至 6 服务器 + backend/tools 遮蔽修复, Sep 11)
- **新增 3 个元典 MCP 服务器**（用户提供的官方配置）：合同审查 `contract-review`、证券合规 `securities`、幻觉校验 `hallucination`——总计 **6 个服务器**（law/case/company/contract-review/securities/hallucination）
- **配置要点**：双配置文件同步（backend/config.yaml + backend/.hermes/config.yaml）；新服务器统一 `sampling: {enabled: false}`（已验证上游 SamplingHandler 模块尊重该开关——禁用时 `_sampling=None` 不声明 capability，元典 Java 服务器安全）；全部 6 个补齐 `Accept: application/json, text/event-stream` 头（对齐元典官方配置）
- **重大发现——backend/tools 空壳包遮蔽**：`backend/tools/__init__.py`（内容仅"# LawClaw 法律工具包"注释）作为正则包**完全遮蔽根 tools/**，导致后端进程里上游 MCP 七模块（含 mcp_tool_discovery）不可达——**MCP 工具发现从未在同步后的底座上运行**（list_mcp_servers 只读 config 所以显示正常，极具迷惑性）。删除 backend/tools 后 tools 正确解析到根（legal_search/mixture_of_agents 本就在根 tools/，无损失）
- **验证**：重启后 6 服务器全部 enabled；audit 12/12（断言 3→6）
- **同步方法论教训**：上游重构拆分模块后，`list_xxx` 类"读配置"接口的通过不代表"实际功能"正常——工具注册类验证要看运行时 import 路径（`python -c "import tools; print(tools.__path__)"`）

### Done (发行链路端到端实证 — portable 全链闭合, Sep 11)
- **portable 形态端到端实测通过**：release/payload + LawClaw.exe + WebView2Loader.dll → 启动 → **9876 由 payload 内捆绑 runtime 拉起**（CommandLine: `D:\LawClaw
elease\payloadackend
untime\Scripts\python.exe main.py --ws`，父进程 = lawclaw.exe 12356）→ 无障碍点击关窗 → 9876 释放、后端终止、应用 exit 0
- **构建脚本修正**（scripts/build_release.py）：tauri step 补 MinGW PATH 前缀（缺 crt2.o 报错的根因——之前两次"资源映射失败"其实是 PATH 缺失）；overlay 映射修正为目录形式 `{"../release/payload": "./"}`（glob+空 target 不生效）
- **发行产物**：NSIS 118MB / MSI 152MB（含 344MB payload 压缩）；portable 需额外拷 `target/release/WebView2Loader.dll`（脚本待补此步）
- **venv 细节**：runtime venv 的 python.exe 是 launcher，真实进程路径为 base Python——判断是否捆绑运行时要用 CommandLine 而非进程路径

### Done (发行链路 — uv 运行时打包形态定案, Sep 11)
- **PyInstaller 路线判死（当前环境）**：6.22.2 可装可跑，但 Analysis 阶段 RecursionError——lxml 排除后转移到 openpyxl 钩子，setrecursionlimit(20000) 与 threading.stack_size(128MB) 均无效（日志 `backend/build_log.txt`；spec `backend/lawclaw-backend.spec` 保留）。判定为 PyInstaller 对 py3.14 的兼容成熟度问题，等上游修复
- **uv 运行时打包形态定案（12/12 发行级验证）**：
  - `backend/runtime/` = uv venv（py3.14）+ 16 个包（openai/websockets/pyyaml/mcp/pymupdf/pymupdf4llm/jieba/python-docx/openpyxl/pdfminer.six/requests/httpx/aiosqlite/python-dotenv）——**仅 16 包即跑通全功能**（重构后的上游核心依赖极轻）
  - 发行形态：`LawClaw.exe + backend/{runtime/, main.py, doc_intel.py, agent/, tools/, config.yaml, .env, .hermes/, skills/}`
  - **发行级验证**：`runtime/Scripts/python.exe main.py --ws` → audit 套件 12/12（元典 MCP/法条检索/LLM chat 全通）
  - Tauri `spawn_backend` 增加捆绑运行时优先分支（`runtime/Scripts/python.exe` 存在即用，否则 LAWCLAW_PYTHON → PATH）
- **注意**：backend/runtime 不进 git——安装器打包时由脚本重建（`uv venv runtime + uv pip install`）
- **待做**：安装器整合脚本（Tauri 资源打包含 backend/runtime + 排除 .hermes 运行时数据）；真机安装验证

### Done (MinerU 解析 PoC — 结论:pymupdf4llm 留任默认, Sep 11)
- **环境**：MinerU 全版本要求 Python <3.14（本机 3.14.2 不兼容）——用 uv 装独立 cpython-3.13.12 + `.venv313` 隔离环境解决（系统 Python 未动）
- **复杂版式 PoC**（pymupdf 绘制表格+多段判决书，`backend/tests/poc_mineru.py` + `backend/tests/.mineru_poc/` 输出）：
  - **pymupdf4llm 13/13 关键字命中，markdown 管道表格**；MinerU 13/13 命中，HTML 表格——数字版 PDF 上两者等价
  - MinerU 真正差异化（扫描件/图片型 PDF）本 PoC 未覆盖（生成的测试件是文本型）
  - 环境成本实录：3.2GB 模型（ModelScope 源）、首次下载曾僵死需重试、CPU 推理较慢、需独立 venv
- **决定**：**pymupdf4llm 留任默认后端**（零额外依赖、等价质量）；MinerU 作为扫描件升级位（.venv313 已备、用法已写入 requirements-docintel.txt）
- **教训**：subprocess 挂起时日志缓冲不可见——长跑子进程一律 `python -u` + 输出落盘

### Done (LightRAG 案件知识库 PoC — 结论:暂不采用, Sep 11)
- **PoC 脚本**：`backend/tests/poc_lightrag.py`（判决书 PDF → doc_intel 抽取 → LightRAG 图谱构建 → 三模式中文检索），可复测
- **验证通过的部分**：lightrag-hku 1.5.7/1.5.4 均可在 Python 3.14 安装；**LLM 中文实体抽取 15-17s 完成且未被限流卡死**（核心关切解除）；图谱/实体/关系/文档状态全部落盘
- **阻塞的部分（上游 bug 区）**：自定义 embedding 的向量持久化失败——1.5.7 写坏格式（matrix 1368×1，1368 恰为 256×float32 的 base64 长度，疑似 base64 字符串被逐字符写入矩阵）；1.5.4 静默为空（data=0 无报错）。层1 EmbeddingFunc 实测正常（ndarray 2×256），问题在 LightRAG 存储管线内部
- **决定**：知识库维持 **BM25 v0**（`doc_intel.kb_search`，已验证可用）；GraphRAG 升级等 lightrag 修复后重跑 PoC（脚本已留）；若需立即上 GraphRAG 可试 RAG-Anything 全家桶（重依赖）或 Neo4j 后端
- **注意**：RAG-Anything 评估中"Agnes hub 无 embedding 端点"（/v1/embeddings 对该 key 无效）——真语义向量需要 Ollama 本地模型或付费 embedding 服务，这是所有向量方案的前置条件

### Done (上游同步 — hermes-agent 2026-09-11 版重新对基, Sep 11)
- **决策**：上游 fork 点（5/29）以来结构性巨变（run_agent 4590→1556 行 Mixin 化、mcp_tool 3711→704 行拆 7 子模块、hermes_state 拆 24 子模块、新增 26 根模块），评估后立项重新对基
- **安全网**：补 .gitignore（.env/.hermes/target 等排除）+ git init 基线快照 `8198f27`（1330 文件，密钥未入库）——**回滚 = `git reset --hard 8198f27`**
- **方法**：克隆上游 depth-1（`D:\Down\hermes-upstream`）→ 覆盖 Hermes 管理的包树（run_agent/agent/tools/providers/hermes_cli/cron/gateway/plugins/acp_adapter + 根全部 .py）→ 保留本地增量（backend/ 整体、tools/legal_search.py + mixture_of_agents_tool.py、agent/google* 三件、skills/ 整体、src*/scripts/seed、AGENTS.md/README）
- **集成面实测存活**：AIAgent 构造参数与三回调（tool_start/complete/thinking_callback）在上游 Mixin 化后原样存在；`run_conversation` 经 TurnFacadeMixin 包装仍可用
- **我方旧补丁退役**：7 月手修的 `_MCP_NEW_HTTP` 漏判已被上游更完整方案取代（新旧 SDK API 名双兼容，处理 mcp 2.0 移除旧名）
- **上游增量收益**：MCP 七模块架构（transport/server_run/health/sampling/discovery/common/config）+ 进程死亡监督器 + 发现冷却 + stdio 预检——元典 SSE 服务器稳定性增强；**元典 `sampling: {enabled: false}` 配置在新 SamplingHandler 模块下验证仍被尊重**（list_mcp_servers=3 全通）
- **迁移中修复**：补齐 24 个 hermes_state_* 子模块 + hermes_bootstrap/startup_watchdog + registration_lifecycle 等（根 .py 整体覆盖解决）；main.py 导入迁移到新路径 `tools.mcp_tool_discovery`（旧路径 2026-09-14 移除）；补装上游新依赖 `concurrent-log-handler`
- **验证**：四套后端测试 **31/31**（audit 12 + agui 7 + iteration1 7 + doc_intel 5）、vue-tsc 零错误、build 通过；git 提交 `3357e56`（基线 `8198f27` 可回滚）
- **后续注意**：上游 config schema 新键（honcho/identity_signature 等）未引入——当前 config.yaml 旧键被容忍；下次上游同步直接重跑本流程即可（git 历史里有完整方法）

### Done (Tauri 后端生命周期端到端验证 + 全局经验召回, Sep 11)
- **Tauri 自启停端到端实测通过**（发行阻塞#4 的机制闭环）：
  - `pnpm tauri dev`（清空 9876/1420 后启动）→ 桌面窗口打开 → **python 后端被 Rust 侧自动拉起**（9876 LISTENING，前端 AG-UI 步骤面板正常连上自动拉起的后端）
  - 无障碍点击窗口"关闭"按钮 → **9876 立即释放、后端进程被杀**、tauri dev 退出（exit 0）
  - 实操细节：computer-use 帧因页面动画持续失效，改用 get_app_state 无障碍树定位"关闭"按钮（元素 AXPress）成功
- **经验记忆增强**：`db.getAllTimelineEvents()`（store.getAll 全库读取）+ timeline store `loadAllEvents()`（合并式，不覆盖当前案件视图）+ chat.ts 经验召回前懒加载全量时间轴——**跨案件决策/里程碑全部进入召回语料**（此前只有当前案件已加载的事件）
- **环境**：验证后已恢复 vite(1420) + 后端 --ws(9876)

### Done (开源研究收口 — 文档智能层 + Tauri 后端生命周期, Sep 11)
- **六项目评估收口**（opendataloader-pdf / RAG-Anything / cognee / openmemory(LongMemory) / ruflo / semantica→已落地）：选型地图——解析+知识库主干选 **RAG-Anything**(中文主场、格式最全)；记忆层 **cognee vs LongMemory** 待同题 PoC；**ruflo** 不接入（多智能体蜂巢不适合律师产品，抄 GOAP 规划思想于远期流程引擎）；openmemory 壳的**引用计数自启停**模式已移植
- **①文档抽取适配层**（新 `backend/doc_intel.py`，借鉴 opendataloader/RAG-Anything 评估）：
  - 适配链可插拔降级：PDF = pymupdf4llm(Markdown 最佳) → pymupdf → pdfminer；DOCX=python-docx；XLSX=openpyxl；文本类直解；`register_extractor()` 预留 raganything/opendataloader 升级位
  - 依赖：`backend/requirements-docintel.txt`（pymupdf==1.28.2 + pymupdf4llm==1.28.2 + jieba==0.42.1，均可选增强，未装则优雅降级到 pdfminer）
  - **实测**：中文判决书 PDF 抽取命中"500万元/海淀区"；DOCX 命中保密条款
- **②案件知识库 v0**：按案件分库 BM25（jieba 分词，缺失退化 bigram），语料指纹缓存防重复分词；RPC `kb_search`；chat 自动注入：前端传该案件已解析文件（≤8 篇×30K 字）→ 后端按用户问题选 top5 片段注入 `[案件文档库检索结果]`
- **③经验记忆 v0**：RPC `experience_search`；chat 自动注入跨案件描述 + 本案决策/里程碑（top3，`[历史经验召回]`）——"我的判例库"检索地基
- **chat 附件革命**：PDF/DOCX/XLSX 从"[二进制文件占位符]"变为真实内容进 LLM（`[附件: 判决书.pdf（解析器: pymupdf4llm, N 字符）]`）。**实测：AI 从判决书 PDF 准确答出判决金额"500万元"**
- **前端**：ManagedFile/FileRecord 增 `extractedText/extractor`；上传即后台解析入库（parseAndStoreExtracted）；FilePanel 搜索覆盖全文 + "✓ AI可读"徽章 + 已解析 PDF/Office 文本预览；chat.ts 发送 `matter_documents/matter_id/experience_items`
- **④Tauri 后端生命周期**（借鉴 openmemory-manager 引用计数）：lib.rs 启动时拉起后端（9876 已监听则跳过；`--ws` 模式规避 stdin-EOF 退出缺陷；CREATE_NO_WINDOW），窗口 Destroyed 引用计数归零杀进程 + RunEvent::Exit 兜底；backend 目录解析 LAWCLAW_BACKEND_DIR → CARGO_MANIFEST_DIR/../backend（dev）→ exe/backend（release）；cargo check 通过
- **新增 RPC**：`parse_document` / `kb_search` / `experience_search`
- **回归**：新 `tests/test_doc_intel.py` 5/5（PDF 中文抽取/DOCX/知识库命中/经验召回/**chat 附件全链路答出"500万元"**）、audit 12/12、agui 7/7、iteration1 7/7（第二轮）、vue-tsc 零错误、build 通过、cargo check 通过
- **注意**：GUI 上传流程的"AI可读"徽章需真实文件对话框（IAB 无法驱动），人工验证即可； HANDLE：chat 注入块修复过 `params` 未定义 bug（handle_chat 参数已解构，新参数须入签名）

### Done (Semantica 借鉴 — 双时间线期限 + 决策记录, Sep 11)
- **参考仓库**：`D:\databi\semantica`（"开源版 Palantir"，知识图谱+决策智能+溯源，MIT，18 万行）。评估结论：**概念捐助者而非依赖**（中文 NLP 为零、核心依赖含 torch/opencv）；抄设计不引包
- **双时间线期限模型（schemaVersion 3→4，借鉴 BiTemporalFact）**：
  - `DeadlineItem` 新增 `validFrom`（版本生效）/`supersededAt`（被取代时间，null=现行）/`history[]`（DeadlineRevision：完整旧版本+有效期窗口+changeReason）
  - 迁移**自愈式**（按字段缺失判断，与版本号解耦——种子/旧数据直接标 v4 也能补齐）
  - `updateDeadline`：type/date/note/customLabel 实质性变更自动把旧版本关窗（validUntil=now）推入 history；completed 翻转不算修订
  - `removeDeadline` 改为**软撤销**（关窗留痕可恢复），新增 `restoreDeadline`（重新开窗，历史保留）
  - 消费端全部排除 superseded：getActiveDeadlines/getNearestDeadline（caseConstants）、Dashboard 紧急期限、schedule 通知重调度、chat 案件上下文注入、CaseDetail 列表
- **UI（CaseDetailView）**：期限行新增「编辑」（双模式复用添加对话框，编辑带"变更原因"输入）与「修订 N」徽章→修订历史对话框（当前状态+版本时间线+已撤销横幅+恢复按钮）；删除改「撤销（可恢复）」确认文案；标题旁「已撤销 N 项（点击查看/恢复）」→已撤销列表对话框（修复"撤销后无恢复入口"缺口）
- **决策记录（借鉴 Decision-as-first-class）**：TimelineEventType 新增 `'decision'`；案件时间轴「记录决策」按钮→对话框（决策事项/考虑过的方案/结论/理由）存入 IndexedDB 时间轴（metadata 保留结构化字段，供未来"我的判例库"检索）；时间轴渲染金色 ⚖ 决策徽章
- **验证**：vue-tsc 零错误、build 通过；数据层 GUI 实测通过（迁移落盘 schemaVersion=4、编辑留痕 hist=1 且旧版本完整）；撤销→恢复/决策对话框的交互路径因 IAB 测试环境页面状态不稳定改为人工验证（localhost:1420），逻辑由类型系统与 Pinia 绑定保障
- **环境备注**：长跑的 vite dev 会话多次 HMR 后 transform 缓存可能滞后/卡死（served 代码与磁盘不一致）——重启 `pnpm dev` 解决

### Done (AG-UI 官方协议对齐 + LiveKit 架构借鉴, Sep 11)
- **参考仓库**：`D:\Down\ag-ui-main`（AG-UI 官方 monorepo，规范源 `sdks/typescript/packages/core/src/events.ts`）+ `D:\Down\livekit-master`（LiveKit Server Go SFU）
- **协议对齐（合规测试 7/7：`backend/tests/test_agui_protocol.py`）**：
  - EventEmitter 每事件自动注入官方 `timestamp`(ms epoch)
  - `RUN_STARTED` 补官方必填 `threadId`（= 会话 ID，前端 chat RPC 传 `thread_id`，三处 emitter 构造点贯通）
  - 错误终止改用官方 `RUN_ERROR`（message 为顶层字符串 + code），与 `RUN_FINISHED` **互斥**——handle_chat 四处错误路径已改，中断路径保留 outcome:interrupt
  - `STEP_STARTED/FINISHED` 补官方必填 `stepName`（emitter 内部 `_step_names` 记账，无需改调用点）
  - `TOOL_CALL_START` 补 `toolCallName` + `parentMessageId`；`TOOL_CALL_RESULT` 补官方必填 `messageId` + `content`（emitter 内部 `_tool_msg_ids` 记账）
  - `REASONING_CONTENT` → 官方名 `REASONING_MESSAGE_CONTENT`（THINKING_* 已废弃；前端仅经 legacy 回调消费推理，无破坏）
  - `ACTIVITY_STARTED/ENDED`（非官方）→ 官方 `ACTIVITY_SNAPSHOT/ACTIVITY_DELTA` schema
  - 握手 `ag_ui_version` 0.1 → **0.2**；保留全部 LawClaw 扩展字段（官方 zod passthrough 允许）
- **前端对齐**：types/legal.ts 全部事件接口按官方字段更新（RunErrorEvent 顶层 message、Step/Tool 事件补字段）；chat store 新增 RUN_ERROR 分支（runFailed + 步骤标 failed）；sendMessage 传 `thread_id`
- **LiveKit 借鉴——每连接串行泵**：WsServer per-connection `chat_lock`（LiveKit rtcSessionWorker 模式）：同连接同时只允许一个 chat run，重复请求返回 -32002 中文忙错误；abort/ping/检索不受锁限（"停止"始终可达）
- **LiveKit 结论**：该仓库是 Go SFU 服务端（无 agents SDK）；语音能力需另引 `livekit/agents`，当前文本对话架构暂不集成，事件协议已具备未来承载音频事件的扩展位（CUSTOM/ACTIVITY_*)
- **回归**：原 12 项套件 12/12、迭代1 功能 7/7、协议合规 7/7、vue-tsc 零错误、build 通过；GUI 冒烟确认步骤面板/工具卡片/RUN_ERROR 失败态在新事件流下正常渲染
- **GUI 注意**：IAB/后台标签页中 bootstrap 定时器被节流，启动可能明显变慢——非 bug（document.hidden 节流，前台正常）

### Done (UI 深度打磨 — 第二轮走查, Sep 11)
- **紧急期限标签分级**：Dashboard 右侧标签从清一色"紧急"改为三级 `deadlineStatusLabel()`——已逾期(danger)/今天到期(danger)/紧急≤7天(warning)/临近(info)；逾期行加深红底纹（`.deadline-overdue`），`urgency` 类型扩为 'overdue'|'critical'|'warning'
- **演示案件期限全量修复**：matter.ts 内部数组中天行/赵某/孙某/恒大的 deadline 从过去日期改为未来（t(-30)/t(-20)/t(-25)/t(-30)），案件卡警告不再满屏"逾期 N 天"，只剩刻意保留的测试案件+周某紧急项
- **日程种子时区 bug**：`schedule.ts` base 从"今天08:00"改为"今天00:00"——原实现 h 参数语义混乱（08:00+16.5h=次日凌晨00:30 出现"凌晨开会"）
- **日程类型徽章统一**：CalendarPage 截止期限也显示徽章；开庭类型用红描边徽章 `.cp-court-tag`（两处列表模板同步）
- **开发工具隐藏**：页脚"恢复演示数据/通知测试"包在 `import.meta.env.DEV` 内，生产构建不显示
- **折叠侧栏布局**：折叠态移除孤立展开按钮，改为点 logo 整行展开（hover 反馈），删除未用的 Expand 图标导入
- **回归**：vue-tsc 零错误、vite build 通过；暗/亮双主题 + 960x600 最小窗口 GUI 走查通过（960 下侧栏自动折叠为图标栏）

### Done (UX 迭代 1 — 深度评审修复, Sep 11)
- **深度评审完成**：全链路 GUI 实测（向导/工作台/建案/对话/日程/技能/专家/文件/设置）+ 12 项后端集成测试；评审结论与问题清单见会话记录
- **P0-1 首启向导修复**：`src/main.ts` 曾无条件预写 `apiKey:'demo-mode', completed:true` 导致向导成死代码、新用户对话必败。已移除预写；`main.py:_make_agent` 对 `demo-mode` 占位 key 回退 `.env` 默认（兼容老用户）
- **P0-2 建案弹窗修复**：`CaseCreateDialog.vue` el-dialog 加 `append-to-body`——此前 overlay 挂在 231px 侧栏 `.matter-list` 内被裁剪成窄条且"取消关不掉"（5 个实例并存，关的是另一个）
- **P1 技能中文名**：`main.py` 新增 `SKILL_DISPLAY_NAMES`（26 个启用技能的中文映射），`list_hermes_skills` 输出中文名；SkillPage 描述改两行截断+省略号
- **P1 对话失败体验**：后端 `_friendly_llm_error()`（429 限流/401 Key 无效/欠费/超时/模型名错误 → 中文可行动提示）+ 返回值带 `error:true`；前端 Message/BackendChatResponse 加 `error` 字段，错误气泡红框+提示行，步骤面板新增失败态（红 ✗ "处理失败"），chat store 新增 `runFailed`
- **P1 种子数据相对日期**：`matter.ts` 内部演示数组（周某 t(-3)/天行开庭 t(-7)/刘某 t(-12)）与 `seedCaseData.ts`、`schedule.ts`（基准=今天08:00）全部改为相对当前日期，保留 2 项逾期做演示；工作台现在显示健康的紧急度分层 + 今日待办有条目
- **P1 元典检索查询改写**：`handle_legal_search` 两级改写——`_rule_rewrite_query` 规则短语整句替换（命中即返回，避免子串拼接复读 bug）+ 0 结果时 `_llm_rewrite_query` LLM 改写重试（8s 超时回退）；返回 `query_used/rewritten` 供调试
- **P2 `test_llm` RPC**：真实调用最小补全验证 Key/地址/模型（比 initialize 的 configured 检查可靠），错误经本地化；设置页与向导第一步都用它，向导文案同步修正
- **P2 设置页居中**：`.sv-body` max-width 860px 居中
- **创新 .ics 导出**：`src/lib/ics.ts`（RFC5545 折行/转义/UTC）+ CalendarPage「导出日历 (.ics)」按钮，可导入手机日历
- **创新 Word 导出**：后端 `handle_export_docx`（python-docx，宋体/黑体/首行缩进法律文书格式，Markdown 标题/列表/粗体解析）+ `export_docx` RPC；前端 `lib/docxExport.ts` 共享助手；FilePanel 右键菜单与 ChatPanel 消息工具栏均有"导出 Word"
- **回归验证**：新功能测试 7/7（`backend/tests/test_iteration1.py`）、原 12 项套件 12/12（修正 `list_hermes_skills` 断言为 ≥20 启用制）、vue-tsc 零错误、vite build 通过；GUI 冒烟确认向导/测连接/弹窗/中文名/错误气泡/新种子全部生效
- **评审确认待办（未修）**：安装器仍不含 Python 后端（发行前须做 sidecar/PyInstaller 打包）；`.gitignore` 缺 `.env`/`.hermes/`；Agnes 免费档限流严格，正式使用需用户自带 Key

### Done (Tauri Build, Jul 6)
- **Root cause of `cargo:dev` build script panic**: `tauri-build-2.6.3/src/lib.rs:519` calls `is_dev()` which reads `DEP_TAURI_DEV` from `tauri` crate's `build.rs:261`. This worked once `[package.metadata]` sections were added to `Cargo.toml`.
- **Root cause of `export ordinal too large: 94952`**: MinGW `ld` (and LLD) cannot handle >65535 exported symbols from a Rust `cdylib`. Tauri's DLL exports >94K symbols (all linked crate extern symbols on GNU target). **Fix**: changed `crate-type` from `["staticlib", "cdylib", "rlib"]` to `["rlib"]` — no DLL, no export limit. App statically links everything into the EXE.
- **Installers generated** (release build):
  - MSI: `target/release/bundle/msi/LawClaw_0.1.0_x64_en-US.msi`
  - NSIS: `target/release/bundle/nsis/LawClaw_0.1.0_x64-setup.exe`
- **Project copied** to `D:\LawClaw` (avoids parentheses in path `D:\Down\hermes-agent-main (5)...` that broke MinGW `as` assembler and LLD path parsing)
- **Junction created**: `C:\hermes-lawclaw\src` → original path (preserved for reference)
- **MSYS2 packages added**: `mingw-w64-x86_64-gcc` (for `gcc.exe` needed by `windres`), `mingw-w64-x86_64-lld` (tried as alternate linker, ruled out due to PE ordinal limit)
- **Build dependencies**: PATH must include `C:\msys64\mingw64\bin` for `windres.exe` + `gcc.exe`

## Key Decisions
- **Pinia** for state management over Vuex – simpler API, better TypeScript integration
- **WebSocket on port 9876** for dev frontend–backend communication; stdin/stdout for Tauri production sidecar
- **localStorage** for session/message persistence in dev phase – no SQLite dependency yet
- **`marked`** for markdown rendering in chat bubbles – lightweight, GFM support
- **Practice profile pattern** from `claude-for-legal` cold-start-interview adapted for Chinese lawyers (执业领域, 团队规模, 律所名称)
- **Quick action cards** (法规检索/合同审查/文书起草/诉讼费计算) as dashboard entry points for common lawyer workflows
- **Agent caching by (api_key, base_url, model)** – allows dynamic LLM config changes per request without restart
- **Thread executor for blocking agent.chat()** in async WebSocket handler – prevents event loop stall
- **HERMES_HOME isolation** – `os.environ.setdefault("HERMES_HOME", str(BACKEND_DIR / ".hermes"))` to avoid clobbering user's `~/.hermes/`
- **Migrate from NPC API to 元典开放平台** – NPC Phase II upgrade killed old REST API; 元典 provides free tier (50K credits/month) with MCP (Streamable HTTP SSE) + REST HTTP API
- **MCP servers over direct HTTP API for skills** – the skill packs expect MCP tool names (`yuandian_rh_ft_search`, etc.); Hermes exposes them as `mcp_yuandian_law_yuandian_rh_ft_search` via tool registry
- **元典 MCP config**: 3 servers (law/case/company) with `sampling: {enabled: false}` to avoid protocol mismatch with Java backend
- **LEGAL_AGENT_PROFILE_HOME / LOCAL_DATA_HOME** env vars set to `backend/.hermes/profiles/` and `backend/.hermes/data/` for skill pack compatibility

## Next Steps
1. Run `pnpm tauri dev` and test `/litigation-matter-intake` or `/prc-legal-research-law-search` in a real conversation
2. Remove or replace the 4 basic skills with professional pack equivalents (`contract-review` → `commercial-review`, `legal-research` → `prc-legal-research-law-search`)
3. Install remaining packs (ip-legal 12 skills, ai-governance-legal 9 skills) if needed
4. Set up LEGAL_AGENT_PROFILE_HOME cold-start interview for practice profiles
5. Polish citations display: handle edge cases in article extraction, add copy-to-clipboard

## Critical Context
- Agnes API OpenAI-compatible: `POST https://apihub.agnes-ai.com/v1/chat/completions` with model `agnes-2.0-flash`
- Backend WebSocket server on `ws://127.0.0.1:9876` – frontend connects automatically
- `handle_chat()` accepts optional `api_key`, `base_url`, `model` per request (from frontend setupStore)
- Agent cache keyed by `f"{api_key}:{base_url}:{model}"` – no restart needed for LLM config changes
- Skills loaded from `HERMES_HOME/skills/` (`backend/.hermes/skills/`) via `agent/skill_commands.py`
- MCP servers configured under `mcp_servers` key in `backend/.hermes/config.yaml` (copy of `backend/config.yaml`)
- `discover_mcp_tools()` called explicitly in `backend/main.py` at module level (not automatic via model_tools)
- `hermes_bootstrap` skipped via `skip_context_files=True, skip_memory=True` to avoid Hermes system prompt interference
- WebSocket `ping_interval=None` required – LLM calls can take 20-30s which exceeds default 20s keepalive timeout
- **NPC API dead**: `https://flk.npc.gov.cn/api/` (GET with `searchType`, `sortTr`, `page`, `size` query params) now serves SPA HTML. The old API returned JSON with `result.data[].{id,title,gbrq,jgmc,sxx}`. New Phase II site (Aug 2025) is Vue Router SPA; search API is client-side only
- **元典 MCP** (Streamable HTTP SSE): 6 servers at `open.chineselaw.com/mcp/{law,case,company,contract-review,securities,hallucination}/stream`, Bearer auth via `YUANDIAN_API_KEY`（环境变量，**Key 不入库**）. Java backend rejects `SamplingCapability.tools` — must set `sampling: {enabled: false}`
- **元典 HTTP API fallback**: `POST https://open.chineselaw.com/open/rh_fg_search` with `X-API-Key` header, used by `handle_legal_search()` in `tools/legal_search.py`
- **6 legal skill packs** from 元力工场: litigation (19), ip (12), commercial (12), corporate (13), legal-research-cn (4), ai-governance (9). Format: bundle.json → SKILL.md → profiles/ → connectors/ → workflows/. install.py auto-detects 8 agent frameworks. Data source: 元典 MCP + Tavily. 4 packs installed (48 skills), verified as slash commands
- MCP tool names in Hermes follow convention: `mcp_{sanitized_server}_{tool_name}` (e.g., `mcp_yuandian_law_yuandian_rh_ft_search`)
- Matter stages (案件阶段): 待处理 → 审查中 → 证据收集 → 诉讼中 → 调解中 → 已完成 → 已归档
- LawClaw: 52 skills (48 pro + 4 basic) + 53 MCP tools = 125 total tools

## Relevant Files
- `LawClaw/backend/main.py`: Dual-protocol JSON-RPC server (stdio + WS 9876), agent caching, env var setup, MCP discovery, `handle_legal_search()` (元典 HTTP API), `setup_save` endpoint
- `LawClaw/backend/config.yaml`: Skills enabled, MCP server configs (3 元典 SSE), display branding
- `LawClaw/backend/.hermes/config.yaml`: Copy of config.yaml (MCP discovery reads from HERMES_HOME)
- `LawClaw/backend/.hermes/`: Isolated HERMES_HOME with skills/, profiles/, data/, config.yaml
- `LawClaw/backend/.env`: API keys (OPENAI_API_KEY, YUANDIAN_API_KEY)
- `LawClaw/backend/.hermes/skills/`: 52 skill directories (4 basic + 48 professional)
- `LawClaw/tools/mcp_tool.py`: MCP server lifecycle, bugfix at line 1432 (`_MCP_HTTP_AVAILABLE or _MCP_NEW_HTTP`)
- `LawClaw/tools/legal_search.py`: Rewritten to 元典 HTTP API
- `LawClaw/src/`: Vue 3 + Element Plus frontend (types, stores, components, lib)
- `LawClaw/src-tauri/`: Tauri desktop shell (window 1280x800, sidecar, shell plugin)
- **Skill packs** (local copies):
  - `D:\Down\toolkits_legal-skillpack-litigation-legal/` — 19 skills (installed)
  - `D:\Down\toolkits_legal-skillpack-legal-research-cn/` — 4 skills (installed)
  - `D:\Down\toolkits_legal-skillpack-corporate-legal/` — 13 skills (installed)
  - `D:\Down\toolkits_legal-skillpack-commercial-legal/` — 12 skills (installed)
  - `D:\Down\toolkits_legal-skillpack-ip-legal/` — 12 skills (not installed)
  - `D:\Down\toolkits_legal-skillpack-ai-governance-legal/` — 9 skills (not installed)
