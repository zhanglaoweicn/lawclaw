# LawClaw 律爪 — 律师智能体

面向中国执业律师的桌面 AI 智能体。基于 [Hermes-agent](https://github.com/NousResearch/hermes-agent) 二次开发。

> **想研究本项目**：先读 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)（分层与数据流），
> 再看 [AGENTS.md](AGENTS.md)（完整过程日志：决策、踩坑、实测记录，信息量最大）。

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
    ├── build_release.py    # 发行构建（双风味：demo 演示版 / clean 客户版）
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

## 本地构建桌面端应用（双风味）

同一套代码产出两种交付物，差别只在**首启是否有演示数据**与**是否携带密钥**：

| | `demo` 演示版 | `clean` 客户版 |
|---|---|---|
| 首启数据 | 自动灌入虚构演示案件（10 案，含期限/日程/会话） | **空台账**，无任何演示数据 |
| 密钥 | **默认不含**（可选注入，见下） | **强制不含**（传 `--with-*-key` 会直接报错退出） |
| 安装标识 | `com.lawclaw.demo` / 产品名 `LawClaw-Demo` | `com.lawclaw.app` / 产品名 `LawClaw` |
| 页脚 | 保留「重置演示数据」（演示前一键回到初始态） | 无 |

两种标识分开，**可同机并存且 localStorage 互不污染**（演示数据不会串进客户环境）。

```bash
# 演示版（含捆绑 Python 运行时 + NSIS/MSI 安装器）
python -X utf8 scripts/build_release.py --flavor demo

# 客户版
python -X utf8 scripts/build_release.py --flavor clean

# 只想快速验证 payload（跳过运行时与安装器，约 1 分钟）
python -X utf8 scripts/build_release.py --flavor clean --skip-tauri --skip-runtime
```

产物：

```
release/payload-demo/           # 便携目录（可直接拷 U 盘运行，见下方「便携形态」）
release/payload-clean/
src-tauri/target/release/bundle/nsis/LawClaw-Demo_0.1.0_x64-setup.exe   # 演示版安装器
src-tauri/target/release/bundle/nsis/LawClaw_0.1.0_x64-setup.exe        # 客户版安装器
```

默认只出 **NSIS** 安装器（Windows 主力形态，体积更小，不依赖 WiX）。需要 MSI 时：

```bash
python -X utf8 scripts/build_release.py --flavor clean --bundles "nsis,msi"
```

> MSI 走 WiX 工具链；本机在含 onnxruntime/lxml 的大 payload 上 `light.exe` 会失败，
> 如需 MSI 请先在另一台机器或干净环境验证。

脚本末尾会做**发布物自检**：确认没有把 `.hermes/{sessions,memories,logs,state.db}` 等运行时数据
和任何密钥带出去。

### 便携形态（免安装）

安装器之外，也可以直接拷目录运行：把 `release/payload-<flavor>/` 的内容与
`src-tauri/target/release/lawclaw.exe`（重命名为 `LawClaw.exe`）、
`src-tauri/target/release/WebView2Loader.dll` 放在**同一个目录**下，双击 exe 即可
（exe 会在自己所在目录找 `backend/`）。此形态需目标机已装 WebView2 运行时
（Win10 1804+ / Win11 通常自带）。

### 演示机免配置（可选，仅限你自己保管的演示机）

演示时若不想现场填 Key，可把开发机 `backend/.env` 的凭证写进产物：

```bash
python -X utf8 scripts/build_release.py --flavor demo --with-llm-key --with-yuandian-key
```

⚠ 该产物**内含真实密钥**，只能留在自己的演示机上，**绝不可**交给客户或上传公开渠道。
客户版没有这个开关。

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
