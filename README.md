# LawClaw 律爪 — 律师智能体

面向中国执业律师的桌面 AI 智能体。基于 [Hermes-agent](https://github.com/NousResearch/hermes-agent) 二次开发。

## 快速开始（三条路）

| 我想… | 怎么做 | 需要预装 |
|---|---|---|
| **直接用** | 到 [Releases](../../releases) 下载 `LawClaw_x.y.z_x64-setup.exe` 安装 | 无（安装包已内嵌 Python 运行时） |
| **免安装/拷 U 盘** | 解压 `portable-*.zip`，双击目录里的 `LawClaw.exe` | 无 |
| **改代码 / 自己打包** | 见 [docs/DEPLOY.md](docs/DEPLOY.md) 的方式 C 与 D | Python ≥3.11、Node ≥18、pnpm（打包另需 Rust + MinGW） |

首次启动会进配置向导：填 **API 地址 / 模型 / API Key**（任意 OpenAI 兼容端点）→ 点「测试连接」→ 完成。
法规/案例检索需要另配元典开放平台的 Key（写入 `backend/.env` 的 `YUANDIAN_API_KEY`），不配也能用其余功能。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOY.md](docs/DEPLOY.md) | 部署与运行：四种方式、源码打包双风味、配置项、常见问题 |
| [docs/DATA_PRIVACY.md](docs/DATA_PRIVACY.md) | 数据存哪、什么内容会发往第三方、凭证如何存 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 分层与数据流：想读代码先看这个 |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 第三方组件与内容署名、许可合规 |

## 项目结构

```
LawClaw/
├── src-tauri/          # Tauri（Rust）桌面壳：启停后端、窗口生命周期
├── src/                # Vue 3 + Element Plus 前端
│   ├── App.vue         #   视图编排（工作台/助理/案件/日程/文件/技能/专家/配置）
│   ├── stores/         #   Pinia 状态（matter/chat/schedule/file/timeline/…）
│   ├── lib/backend.ts  #   WebSocket(9876) JSON-RPC 客户端
│   └── lib/db.ts       #   IndexedDB（文件、案件时间轴）
├── backend/            # 本项目的核心增量：LawClaw 自建后端
│   ├── main.py         #   双协议 JSON-RPC 入口（stdio + WebSocket 9876）
│   ├── citations.py    #   法条引用抽取（纯函数）
│   ├── doc_review.py   #   文书细节校对引擎 M1–M8 + 法条时效
│   ├── npc_law.py      #   国家法律法规数据库客户端（官方时效主源）
│   ├── doc_intel.py    #   文档抽取 + 案件知识库(BM25) + 经验召回
│   ├── watchdog.py     #   值守助手（案件扫描 + 定时晨报）
│   ├── config.yaml     #   技能白名单、MCP 数据源、品牌
│   └── .hermes/skills/ #   法律技能库（Apache-2.0，见 THIRD_PARTY_NOTICES）
├── agent/ tools/ providers/ hermes_cli/ cron/ gateway/   # Hermes-agent 底座（MIT，独立维护的 fork）
└── scripts/
    ├── build_release.py    # 发行构建（payload + 捆绑运行时 + 安装器 + 自检）
    └── dev.ps1             # 开发启动
```

## 开发

```bash
# 1. 后端
cd backend
pip install -e ..
python main.py

# 2. 前端 (新终端)
pnpm tauri dev
```

## 本地构建桌面端应用

本产品**只有一个版本**（交付给律师使用）：首启**空台账**，**不含任何内置/测试案件数据**，
**不含任何密钥**（LLM Key 由用户在首启向导里填）。构建脚本里也没有注入密钥的开关。

```bash
# 全量：payload + 捆绑运行时 + 前端 + NSIS 安装器 + 发布物自检/冒烟
python -X utf8 scripts/build_release.py

# 顺带产出免安装便携目录 release/portable/
python -X utf8 scripts/build_release.py --portable

# 只想快速验证 payload（跳过运行时与安装器，约 1 分钟）
python -X utf8 scripts/build_release.py --skip-tauri --skip-runtime
```

产物：

```
release/payload/                              # payload（含捆绑运行时）
release/portable/                             # 便携目录（拷走即用）
src-tauri/target/release/bundle/nsis/LawClaw_0.1.0_x64-setup.exe   # NSIS 安装器
```

默认只出 **NSIS** 安装器（Windows 主力形态，体积更小，不依赖 WiX）。需要 MSI 时：

```bash
python -X utf8 scripts/build_release.py --bundles "nsis,msi"
```

### 首启流程（客户版）

1. 首次启动 → 配置向导第 1 步填 **API 地址 / 模型 / API Key**（支持任意 OpenAI 兼容端点），
   点「测试连接」验证后继续；
2. 第 2 步填执业画像（可跳过）；
3. 进来后是**空工作台**，从「案件 → 新建案件」开始建档。

> 说明：客户版**必须先填 API Key 才能进入主界面**（向导以此判定配置完成）。
> 数据源密钥（元典开放平台）目前需写入安装目录下 `backend/.env` 的 `YUANDIAN_API_KEY`；
> 留空时法规检索会提示未配置，其余功能不受影响。

## 数据源

- 北大法宝 MCP — 法规/判例/法条检索
- 元典开放平台 — 法规/案例/企业信息
- 国家法律法规数据库 — 官方法规（免费）

## 通信

- 飞书 / 企业微信（通过 Hermes Gateway）

## 许可与合规

- 本项目以 **MIT** 许可发布（见 `LICENSE`），底座为 Nous Research 的 Hermes-agent。
- 内嵌法律技能内容来自 **Anthropic `claude-for-legal`** 及其中国法本地化版本，
  依 **Apache-2.0** 使用并已声明修改；全文与署名见 `THIRD_PARTY_NOTICES.md`
  与 `licenses/Apache-2.0.txt`。
- 与 Anthropic / Claude **无隶属或背书关系**（Apache-2.0 §6 不授予商标权）。

## 免责声明

本系统为律师辅助工具，所有分析结果仅供参考，不构成正式法律意见。
