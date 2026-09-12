# 第三方组件与内容声明（THIRD_PARTY_NOTICES）

> **本项目许可**：MIT（见 [LICENSE](LICENSE)）。本项目为 Hermes-agent 的二次开发分支，
> 内嵌的第三方组件与法律技能内容另有其自身许可，逐项列于下文与 `licenses/` 目录。
>
> **免责声明**：LawClaw 律爪 是律师辅助工具，全部输出均为「供执业律师复核的草稿」，
> 不构成正式法律意见，不得直接对外出具。

LawClaw 律爪 以 **MIT** 许可发布（见 `LICENSE`）。项目内嵌、改编或参考了以下第三方成果，
其权利归各自权利人所有，并按其自身许可使用。本文件用于满足相关许可的署名与声明义务。

---

## 1. Hermes-agent（MIT）— 项目底座

- 来源：Nous Research 的 **Hermes-agent**（开源 AI Agent 框架）
- 许可：MIT
- 使用方式：**fork 并在仓库内独立维护**（非 submodule、非 pip 依赖）。仓库根下的
  `run_agent.py`、`agent/`、`tools/`、`providers/`、`hermes_cli/`、`cron/`、`gateway/`、
  `plugins/`、`acp_adapter/`、`hermes_state_*.py` 等均来自上游。
- 我方修改：见仓库 git 历史（`feat:` 提交）与 `AGENTS.md` 的「上游同步」条目；主要改动为
  法律垂直化（法律工具、技能库、法律工作台前端）、后端 JSON-RPC 入口 `backend/`、
  MCP 元典六服务器接入、文书校对引擎等。
- 义务履行：保留上游 MIT 版权声明（见 `LICENSE` 首行）。

## 2. claude-for-legal / claude-for-legal-ZH（Apache-2.0）— 法律技能内容

- 来源：
  - **anthropics/claude-for-legal** — Anthropic 开源的律师工作流插件集（skills / agents /
    practice-profile 模板，均为 Markdown 内容层）。
  - **claude-for-legal-ZH** — 上述插件集的中国法本地化版本（社区维护）。
- 许可：**Apache License 2.0**（全文见 `licenses/Apache-2.0.txt`）。
- 使用方式：项目内 `backend/.hermes/skills/` 下的领域技能（litigation / corporate /
  commercial / legal-research-cn / employment / ip / ai-governance / privacy /
  regulatory / product 等，含各目录内的 `CLAUDE.md` 实务画像模板与中国法规则参考文件）
  系由此改编、翻译与本地化而来。技能安装的溯源记录见各技能目录下的
  `.legal-agent-skillpack-install.json`（`package_id: claude-for-legal`）与
  `scripts/cfl_installed.json`。
- **我方作出的修改**（Apache-2.0 §4(b) 要求声明）：
  1. 技能目录与 frontmatter `name` 统一加领域前缀（如 `employment-termination-review`），
     以避免跨插件同名冲突；
  2. 技能内 `~/.claude/plugins/config/...` 等路径改写为本技能目录的绝对路径；
  3. 将指向 Claude 桌面端/Claude Code 的「连接器配置」指引改写为 LawClaw 自身的
     「配置 → 数据源 (MCP)」路径；
  4. 移除「调用 Claude 斜杠命令」等品牌化命令指引；
  5. 部分技能名与描述做了中文化。
- 未主张的权利（Apache-2.0 §6）：本许可**不授予任何商标权**。LawClaw 与 Anthropic /
  Claude 无任何隶属或背书关系。
- 剩余说明：部分技能正文中仍保留对原始工具链的描述性提及（如「Claude Code」），
  属客观来源说明，不表示关联或背书；如需彻底清除可对 `backend/.hermes/skills/` 做一轮
  内容复核（**注意**：这些文本会影响模型行为，请逐条复核，勿全局替换）。

## 3. 元力工场 法律技能包（来源同 claude-for-legal）

- 项目早期引入的 litigation / corporate / commercial / legal-research-cn 四个技能包，
  其安装溯源记录同样标注 `package_id: claude-for-legal`，即其为 claude-for-legal 的
  再打包分发版本；许可与归属以上游 Apache-2.0 为准（见上条）。
- ⚠ **发布前请自行确认**：元力工场的分发包页面/许可条款是否附加了额外限制
  （如使用范围、再分发限制）。仓库内未保存其原始 `bundle.json` 与分发包许可文件，
  公开或商业发布前建议向分发方取得书面确认，或仅保留第 2 条上游来源的技能。

## 4. 方法论借鉴（未复制代码）

以下项目**仅参考其设计思想与规则划分，未复制任何代码**，在此致谢：

- **legal-tools**（MIT，律师维护）— 借鉴其「文书细节校对 M1–M8 维度划分」与
  「NPC 国家法律法规数据库 / 人民法院案例库」数据源思路；
  `backend/doc_review.py` 为面向纯文本文书的**自研实现**，
  `backend/npc_law.py` 为**自研** NPC 二期 API 客户端。
- **semantica**（MIT）— 借鉴「双时间线事实（BiTemporalFact）」与
  「决策即一等公民（Decision-as-first-class）」概念，落地为期限修订留痕与案件决策记录；
  未引入其依赖（含 torch / opencv）。
- **AG-UI 协议**（官方规范）— 后端事件流按该协议对齐（`RUN_ERROR` / `REASONING_MESSAGE_CONTENT` /
  `threadId` / `timestamp` 等），仅为**协议实现**，非代码拷贝。

## 5. 依赖组件的许可

- 前端（`package.json`）：Vue 3、Element Plus、Pinia、marked、DOMPurify、Tauri 等，
  均为 MIT / Apache-2.0 系许可。
- 后端（`backend/requirements-runtime.txt`）：openai、websockets、mcp、pymupdf、
  jieba、python-docx、openpyxl、pdfminer.six 等，均为 MIT / BSD / Apache-2.0 系许可。
- 如需逐包清单，可运行 `pnpm licenses list`（前端）与
  `pip-licenses --from=mixed`（后端运行时 venv）。

## 6. 数据与内容合规（发布物须自检）

- **不随包分发**任何真实密钥、客户案件数据、会话记录与运行时状态
  （`backend/.env`、`backend/.hermes/{sessions,memories,logs,data,profiles}` 均已被
  `.gitignore` 排除，且 `scripts/build_release.py` 的发布物自检会拦截）。
- 演示数据（`demo` 风味首启灌入的案件/当事人/案号）**全部为虚构**，与真实当事人无关。
- 法律数据来源（元典开放平台、国家法律法规数据库、人民法院案例库）请遵守各平台
  服务条款；本项目不代为授予这些数据源的访问权。

---

最后更新：2026-09-12
