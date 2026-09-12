# 部署与运行

四种跑法，按"从省事到从源码"排列。**只想用**看方式 A/B；**想改代码**看方式 C/D。

| 方式 | 需要装什么 | 适用场景 | 产物 |
|---|---|---|---|
| A. 装安装器 | 无（只需 WebView2，Win10 1804+/Win11 通常已自带） | 日常使用 | `LawClaw_x.y.z_x64-setup.exe` |
| B. 便携目录 | 无 | U 盘/临时机器/不写注册表 | `portable-<flavor>/` 整目录 |
| C. 从源码运行 | Python ≥3.11、Node ≥18、pnpm 9+ | 开发调试 | — |
| D. 从源码打包 | 方式 C + Rust + MSYS2 MinGW + NSIS | 出交付物 | 安装器 + 便携目录 |

> 方式 A/B 的产物在 GitHub Releases 页面下载。安装包**已内嵌 Python 运行时**，
> 目标机不需要装 Python（这个性质有构建期自检保证，见本文末「运行时如何保证不依赖目标机」）。

---

## A. 安装器

1. 下载 `LawClaw_0.1.0_x64-setup.exe`（客户版）或 `LawClaw-Demo_0.1.0_x64-setup.exe`（演示版）；
2. 双击安装，按向导完成；
3. 首次启动进入配置向导：
   - **第 1 步 API 配置**：填 API 地址 / 模型名 / API Key（任意 OpenAI 兼容端点），
     点「测试连接」验证通过后再继续——**客户版必须先填 Key 才能进入主界面**；
   - 第 2 步律师信息（可跳过，但填了回答会更贴合你的业务）；
   - 第 3 步消息平台（可跳过）；
4. 客户版进来是**空台账**，从「案件 → 新建案件」开始建档；演示版自带 10 个虚构演示案件。

**数据源（可选，建议配）**：法规/案例检索依赖元典开放平台的 API Key。
安装后编辑安装目录下的 `backend/.env`：

```ini
YUANDIAN_API_KEY=你的元典Key
```
重启应用生效。不填也能用——只是检索类功能会提示未配置，其余（对话、文书校对、期限计算、
案件管理、Word 导出、值守提醒）都不受影响。

---

## B. 便携目录（免安装）

```bash
# 把 portable-clean/（或 portable-demo/）整个目录拷到目标机任意位置，双击 LawClaw.exe
portable-clean/
├── LawClaw.exe           ← 入口
├── WebView2Loader.dll
├── LICENSE / THIRD_PARTY_NOTICES.md / licenses/
├── BUILD_INFO.txt        ← 标明风味、是否含密钥、构建时间
└── backend/              ← 后端与技能库（含 runtime/ 自带 Python）
```
`LawClaw.exe` 会在**自己所在目录**找 `backend/`，所以整个目录必须一起拷。
文件都在同一目录，不写注册表（除 WebView2 与用户数据目录）。

---

## C. 从源码运行（开发）

### 前置

- **Python ≥ 3.11**（本项目在 **3.14** 上验证；`pyproject.toml` 里上游留下的
  `requires-python = ">=3.11,<3.14"` 只影响 `pip install -e .`，**不需要装这个包**，
  见下方说明）
- **Node ≥ 18**（CI 用 20）+ **pnpm 9+**（`corepack enable pnpm` 或 `npm i -g pnpm`）
- 不需要数据库；数据落在本地文件与浏览器存储里

### 起后端

```bash
# 1) 建虚拟环境（任选一种）
python -m venv .venv                     # 或：uv venv .venv --python 3.14
.venv/Scripts/activate                   # Linux/macOS: source .venv/bin/activate

# 2) 装后端依赖（16 个包，够跑全功能）
pip install -r backend/requirements-runtime.txt

# 3) 启动（默认监听 ws://127.0.0.1:9876）
python backend/main.py --ws
```

- **不需要** `pip install -e .`：`backend/main.py` 会把仓库根加入 `sys.path`，
  直接就能 import 到 `run_agent`、`agent/`、`tools/` 等底座模块。
- 加 `--ws` 只起 WebSocket（桌面端用）；不加则同时起 stdin/stdout 协议。
- 看到 `[LawClaw] WebSocket server starting on ws://127.0.0.1:9876` 即就绪。
- 未配置元典 Key 时会打印一行提示并跳过检索类 MCP（这是有意的，不是报错）。

### 起前端

```bash
pnpm install --frozen-lockfile
pnpm dev            # 浏览器打开 http://127.0.0.1:1420（热更新，日常开发用这个）
# 或
pnpm tauri dev      # 直接开桌面窗口（会先编译 Rust，首次几分钟）
```

启动后照方式 A 的第 3 步走首启向导填 API Key。

### 可选：本地覆盖配置

后端读取 `backend/.env`（**不要提交到 git**，已在 `.gitignore` 中）：

```ini
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
LAWCLAW_MODEL=deepseek-flash
YUANDIAN_API_KEY=你的元典Key
```
> 注意：前端「配置」页填的 LLM 凭证优先级高于 `.env`（按请求传给后端）；
> 元典 Key 目前只能写在这个文件里（界面尚无入口）。

### 跑测试

```bash
# 无需密钥的纯函数套件（CI 也跑这两个）
python -X utf8 backend/tests/test_citations.py      # 法条引用抽取 14 例
python -X utf8 backend/tests/test_doc_review.py     # 文书校对引擎 22 例

# 需要后端在跑 + 有效 API Key 的集成套件
python -X utf8 backend/tests/test_lawyer_full.py    # 律师全场景 107 例（A~F 分区，可传 A B C… 只跑部分）
python -X utf8 backend/tests/test_release_audit.py  # 发行审计 12 例
```

---

## D. 从源码打包桌面端

### 前置

- 方式 C 的全部前置；
- **Rust**（`rustup`）；Windows 上本项目用 **GNU 工具链**：
  ```bash
  rustup default stable-x86_64-pc-windows-gnu
  # 并安装 MSYS2 的 mingw-w64-gcc（提供 crt2.o 与系统库）：
  #   pacman -S mingw-w64-x86_64-gcc
  ```
- NSIS 由 Tauri 首次构建时自动准备，无需手动装。

### 命令

```bash
# 演示版：首启自动灌入 10 个虚构演示案件
python -X utf8 scripts/build_release.py --flavor demo --portable

# 客户版：首启空台账、无任何密钥
python -X utf8 scripts/build_release.py --flavor clean --portable

# 只想快速验证 payload（跳过运行时与安装器，约 1 分钟）
python -X utf8 scripts/build_release.py --flavor clean --skip-tauri --skip-runtime
```

两种风味的**安装标识不同**（`com.lawclaw.demo` / `com.lawclaw.app`），可同机并存且
localStorage 互不污染。

### 产物

```
release/payload-<flavor>/                              # payload（含捆绑运行时）
release/portable-<flavor>/                             # 便携目录（拷走即用）
src-tauri/target/release/bundle/nsis/LawClaw_0.1.0_x64-setup.exe        # 客户版安装器
src-tauri/target/release/bundle/nsis/LawClaw-Demo_0.1.0_x64-setup.exe   # 演示版安装器
```

### 演示机免配置（可选）

演示时不想现场填 Key，可把开发机 `backend/.env` 的凭证注入产物：

```bash
python -X utf8 scripts/build_release.py --flavor demo --with-llm-key --with-yuandian-key
```
⚠ 该产物**内含真实密钥**，只能留在自己的演示机上，**绝不可**交给客户或上传公开渠道。
客户版没有这个开关（传了会直接报错退出）。

### 构建脚本做了什么（含自检）

1. 组装 payload（Hermes 底座 + `backend/*.py` 全部模块 + 技能库 + 许可文件）；
2. 构建**独立可重定位的 Python 运行时**（见下）；
3. 前端构建（注入 `VITE_LAWCLAW_FLAVOR`）；
4. Tauri 打包（`cargo clean -p lawclaw` 强制 tauri-build 重跑，避免两种风味串味）；
5. **发布物自检**：拦截 `.hermes/{sessions,memories,logs,state.db}` 等运行时数据与任何密钥；
6. **包内后端冒烟**：用捆绑运行时真实启动一次后端并打 RPC（`ping`/技能数/MCP 数/值守扫描）——
   这一步专门拦"漏带模块"这类静态检查抓不到的问题；
7. 组装便携目录。

---

## 运行时如何保证不依赖目标机

打包用的是**独立可重定位 CPython**（自带 `python3xx.dll`、标准库、`vcruntime140.dll`），
依赖装进这一份，而不是开发机上的解释器。构建期会断言：

```python
assert sys.prefix == sys.base_prefix   # 不是 venv；prefix 由自身位置推导
```

早期版本曾用 `uv venv`，其 `pyvenv.cfg` 的 `home` 指向开发机绝对路径——那样在没装 Python
的机器上后端起不来。现在这条断言会让不可重定位的运行时**直接构建失败**，不会再漏出去。

---

## 常见问题

**法规检索没结果 / 提示未配置**
元典 Key 没配。写进 `backend/.env` 的 `YUANDIAN_API_KEY` 后重启。

**对话报「⏳ 模型服务限流」或「🔑 API Key 无效」**
LLM 凭证问题，到「配置」页核对 API 地址/模型/Key，用「测试连接」确认。

**双击 exe 没反应 / 白窗口**
多为缺 WebView2 运行时。装一次
[Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) 即可。

**`pnpm build` 报 `node::OnFatalError` / 退出码 134**
Node 堆不够（尤其在同时跑着 `pnpm dev` 时）：
`export NODE_OPTIONS=--max-old-space-size=4096`（Windows: `set NODE_OPTIONS=...`）。

**Tauri 构建报 `ld: cannot find crt2.o`**
MSYS2 的 mingw64 没进 PATH。把 `C:\msys64\mingw64\bin` 加到 PATH 最前面；
如果 `~/.cargo/bin` 下还有另一套 MinGW gcc，用
`CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER` 指到 msys64 那份。

**MSI 打包失败（`light.exe`）**
改用默认的 NSIS：`--bundles nsis`（默认值就是它）。

**端口 9876 被占用**
已有后端在跑（可能是桌面端拉起的）。先关掉旧实例，或让前端连到它。

---

## 数据存在哪里 / 怎么清空

见 [DATA_PRIVACY.md](DATA_PRIVACY.md)。一句话：案件与文书在**本机**（浏览器 WebView 的
localStorage 与 IndexedDB），后端状态在 `backend/.hermes/`。删掉这两处即彻底清空。
