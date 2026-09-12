# -*- coding: utf-8 -*-
"""LawClaw 发行构建脚本。

产物形态：
  release/payload/
  ├── LawClaw.exe              ← Tauri 构建（--skip-tauri 时缺省）
  ├── run_agent.py, hermes_*.py, utils.py, agent/, tools/, providers/, ...  ← Hermes 底座
  └── backend/
      ├── main.py, citations.py, doc_review.py, config.yaml, ...
      ├── runtime/             ← 独立可重定位 CPython（自带标准库，目标机无需装 Python）
      ├── .hermes/             ← 干净首启：skills/ + config.yaml + 空骨架（无会话/密钥数据）
      └── .env                 ← 不含任何密钥（LLM key 由首启向导填写）

两点产品约定（由脚本保证）：
  1. **不含任何案件数据** —— 本产品不带演示/内置案件，首启即空台账；
  2. **不含任何密钥** —— 脚本里没有注入密钥的开关，构建产物天然无密钥。

用法：
  python -X utf8 scripts/build_release.py                 # 全量（payload + 运行时 + 前端 + 安装器 + 自检）
  python -X utf8 scripts/build_release.py --skip-tauri    # 只组 payload（快速验证）
  python -X utf8 scripts/build_release.py --portable      # 额外产出 release/portable/（免安装形态）
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "release" / "payload"
BACKEND_SRC = ROOT / "backend"

# 发行元数据
PRODUCT_NAME = "LawClaw"
IDENTIFIER = "com.lawclaw.app"
WINDOW_TITLE = "LawClaw 律爪 — 律师智能体"

# 默认 LLM 端点（OpenAI 兼容协议；用户可在首启向导里改）
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-flash"

# 由 main() 赋值的全局开关
# 默认只出 NSIS：Windows 主力安装器，体积更小，且不依赖 WiX 工具链。
# 需要 MSI 时用 --bundles "nsis,msi"（本机 WiX light 在含 onnxruntime/lxml 的大 payload 上会失败）。
BUNDLES = "nsis"

# Hermes 底座：仓库根目录的托管文件/目录（同步自上游，随仓库更新）
ROOT_FILES = [
    "run_agent.py", "hermes_constants.py", "hermes_logging.py", "hermes_state.py",
    "hermes_time.py", "utils.py", "cli.py", "model_tools.py", "toolsets.py",
    "toolset_distributions.py", "trajectory_compressor.py", "batch_runner.py",
    "mcp_serve.py", "registration_lifecycle.py", "hermes_bootstrap.py",
    "hermes_startup_watchdog.py", "setup.py",
]
ROOT_DIRS = ["agent", "tools", "providers", "hermes_cli", "cron", "gateway",
             "plugins", "acp_adapter"]
# 根下还有 hermes_state_*.py 拆分模块
STATE_MODULES = [f for f in os.listdir(ROOT) if f.startswith("hermes_state_") and f.endswith(".py")] if ROOT.exists() else []

# backend 内复制的非 .py 固定文件；.py 模块改用「全部打包」策略——
# 硬编码清单曾漏带 citations.py / npc_law.py / doc_review.py / watchdog.py，
# 导致发出去的包后端一启动就 ModuleNotFoundError（发布前冒烟自检已能拦住这类问题）。
BACKEND_FILES = ["config.yaml", "requirements-runtime.txt"]
# .hermes 里携带的首启内容（skills 是核心资产；运行时状态绝不携带）
HERMES_COPY = ["skills", "config.yaml"]
HERMES_EMPTY_DIRS = ["sessions", "memories", "logs", "data", "profiles", "cache", "hooks", "cron", "sandbox"]

IGNORE_DIRS = {"__pycache__", ".idea", ".vscode", "node_modules", "egg-info"}


def copy_tree(src: Path, dst: Path, exclude_names: set = None):
    exclude_names = exclude_names or set()
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and d not in exclude_names]
        rel = os.path.relpath(root, src)
        dst_root = dst / rel
        dst_root.mkdir(parents=True, exist_ok=True)
        for f in files:
            if f.endswith(".pyc"):
                continue
            shutil.copy2(os.path.join(root, f), dst_root / f)


def step_backend_payload(skip_runtime: bool = False):
    print("── [1] 组装后端 payload ──")
    be = PAYLOAD / "backend"
    # 上一次冒烟测试可能在 payload 根（agent/tools/…）留下 __pycache__，先清干净再组装，
    # 否则会被打进安装器（白增十几 MB）。
    for root, dirs, _files in os.walk(PAYLOAD):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
    # 增量构建：--skip-runtime 时先保住已建好的 runtime（venv 重建要几分钟）
    kept_runtime = None
    if skip_runtime and (be / "runtime").exists():
        kept_runtime = PAYLOAD / ".runtime-keep"
        if kept_runtime.exists():
            shutil.rmtree(kept_runtime)
        (be / "runtime").rename(kept_runtime)
    if be.exists():
        shutil.rmtree(be)
    be.mkdir(parents=True)
    if kept_runtime is not None:
        kept_runtime.rename(be / "runtime")
        print("    （复用了已构建的 runtime）")

    # 随包携带许可与署名文件：发行物本身必须带这些声明（MIT/Apache-2.0 的分发义务）
    for extra in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        src = ROOT / extra
        if src.exists():
            shutil.copy2(src, PAYLOAD / extra)
    lic_dir = ROOT / "licenses"
    if lic_dir.is_dir():
        copy_tree(lic_dir, PAYLOAD / "licenses")

    # 发行物标识
    from datetime import datetime
    (PAYLOAD / "BUILD_INFO.txt").write_text(
        f"LawClaw 律爪 发行物信息\n"
        f"======================\n"
        f"产品名         : {PRODUCT_NAME}\n"
        f"安装标识       : {IDENTIFIER}\n"
        f"首启数据       : 空台账（本产品不含任何演示/内置案件数据）\n"
        f"密钥           : 不含任何密钥（LLM key 由首启向导填写）\n"
        f"安装器格式     : {BUNDLES}\n"
        f"构建时间       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"许可           : MIT（见 LICENSE）；内嵌技能为 Apache-2.0（见 THIRD_PARTY_NOTICES.md）\n"
        f"\n便携运行：把本目录内容与 LawClaw.exe 放在同一目录，双击 exe 即可。\n",
        encoding="utf-8",
    )

    # Hermes 底座（仓库根）
    for f in ROOT_FILES + STATE_MODULES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, PAYLOAD / f)
    for d in ROOT_DIRS:
        src = ROOT / d
        if src.exists():
            copy_tree(src, PAYLOAD / d)

    # backend 源文件：config/依赖清单 + backend 下全部 .py 模块
    for f in BACKEND_FILES:
        src = BACKEND_SRC / f
        if src.exists():
            shutil.copy2(src, be / f)
    py_modules = sorted(p for p in BACKEND_SRC.glob("*.py") if p.is_file())
    for src in py_modules:
        shutil.copy2(src, be / src.name)
    print(f"    后端模块 {len(py_modules)} 个: {', '.join(p.name for p in py_modules)}")

    # 干净 .hermes：skills + config + 空骨架（不带会话/记忆/日志/状态库）
    hermes = be / ".hermes"
    hermes.mkdir()
    for item in HERMES_COPY:
        src = BACKEND_SRC / ".hermes" / item
        if not src.exists():
            print(f"    ! 缺少 .hermes/{item}，跳过")
            continue
        dst = hermes / item
        if src.is_dir():
            copy_tree(src, dst)
        else:
            shutil.copy2(src, dst)
    for d in HERMES_EMPTY_DIRS:
        (hermes / d).mkdir(exist_ok=True)

    (be / ".env").write_text(_env_template(), encoding="utf-8")
    print("    payload/backend 就绪（.hermes skills 携带；不含任何密钥）")


def _env_template() -> str:
    """生成 payload 的 .env：**永不包含任何密钥**（脚本没有注入开关，产物天然无密钥）。"""
    return (
        "# LawClaw 环境变量\n"
        "# LLM 凭证：在应用首启向导或「配置」页填写（不写在这里，避免随包分发）。\n"
        "OPENAI_API_KEY=\n"
        f"OPENAI_BASE_URL={DEFAULT_BASE_URL}\n"
        f"LAWCLAW_MODEL={DEFAULT_MODEL}\n"
        "# 元典开放平台（法律检索数据源）。留空则检索功能提示未配置，需用户填入自己的 Key。\n"
        "YUANDIAN_API_KEY=\n"
    )


def _payload_python(be):
    """payload 内解释器路径：新布局 runtime/python.exe，兼容旧布局 runtime/Scripts/python.exe。"""
    for cand in (be / "runtime" / "python.exe", be / "runtime" / "Scripts" / "python.exe"):
        if cand.exists():
            return cand
    return None

def _find_standalone_python() -> Path:
    """定位一份**独立、可重定位**的 CPython（含 python3xx.dll 与标准库）。

    不能用 uv venv：venv 的 pyvenv.cfg 里 home 指向开发机的绝对路径，
    客户机上没有那个 Python 就起不来（"在我机器上能跑"的经典坑）。
    这里用构建脚本自身解释器的 base_prefix —— 它指向那份独立解释器目录。
    """
    base = Path(sys.base_prefix)
    if not (base / "python.exe").exists():
        raise SystemExit(f"✗ 未找到独立解释器：{base}\\python.exe 不存在")
    if (base / "pyvenv.cfg").exists():
        raise SystemExit(f"✗ {base} 是 venv 而非独立解释器，无法作为可重定位运行时")
    import re as _re
    if not list(base.glob("python3*.dll")):
        raise SystemExit(f"✗ {base} 缺少 python3xx.dll，不是完整解释器")
    return base


def step_runtime():
    print("── [2] 构建捆绑运行时（独立 CPython，可重定位）──")
    rt = PAYLOAD / "backend" / "runtime"
    if rt.exists():
        shutil.rmtree(rt)
    src = _find_standalone_python()
    rt.mkdir(parents=True)

    # 只带运行必需的：解释器本体 + MSVC 运行时 + 扩展 DLL + 标准库（不含 site-packages）
    for f in ("python.exe", "pythonw.exe", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        p = src / f
        if p.exists():
            shutil.copy2(p, rt / f)
    for dll in src.glob("python3*.dll"):
        shutil.copy2(dll, rt / dll.name)
    copy_tree(src / "DLLs", rt / "DLLs")
    copy_tree(src / "Lib", rt / "Lib", exclude_names={"site-packages", "test", "idlelib", "tkinter", "turtledemo"})
    (rt / "Lib" / "site-packages").mkdir(exist_ok=True)
    # 明确不带 pyvenv.cfg —— 独立解释器靠自身位置推导 sys.prefix
    print(f"    解释器就绪 {src} → runtime/（{_dir_size_mb(rt):.0f} MB）")

    # 依赖装进这份运行时（不是开发机的解释器）
    req = BACKEND_SRC / "requirements-runtime.txt"
    subprocess.run([sys.executable, "-m", "uv", "pip", "install",
                    "--python", str(rt / "python.exe"), "-r", str(req)], check=True)

    # 自检：prefix 必须自定位（可重定位），且关键依赖可导入
    probe = (
        "import sys, json, ssl, sqlite3\n"
        "import openai, websockets, yaml, mcp, pymupdf, jieba, docx, openpyxl, requests, dotenv, httpx\n"
        "assert sys.prefix == sys.base_prefix, f'not relocatable: {sys.prefix} != {sys.base_prefix}'\n"
        "print('    ✓ 自定位 prefix =', sys.prefix)\n"
        "print('    ✓ 关键依赖可导入（openai %s / pymupdf %s / jieba ok）' % (openai.__version__, pymupdf.__doc__ or 'ok'))\n"
    )
    r = subprocess.run([str(rt / "python.exe"), "-c", probe], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    print(r.stdout.rstrip() or r.stderr[-800:])
    if r.returncode != 0:
        raise SystemExit("✗ 捆绑运行时自检失败——该产物在没装 Python 的机器上无法运行")


def step_frontend():
    print("── [3] 前端构建 ──")
    env = dict(os.environ)
    # vue-tsc + vite 在大项目上容易撞 V8 默认堆上限（表现为 node::OnFatalError / exit 134），
    # 尤其在同时跑着 vite dev server 时。显式抬高堆上限，避免误判为构建失败。
    env["NODE_OPTIONS"] = (env.get("NODE_OPTIONS", "") + " --max-old-space-size=4096").strip()
    subprocess.run(["pnpm", "build"], cwd=ROOT, check=True, shell=True, env=env)


def step_tauri():
    print("── [4] Tauri release 构建 ──")
    # 发行配置 overlay：把 payload 作为资源打进安装器
    overlay = ROOT / "release" / "tauri.release.conf.json"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    rel_payload = "../" + "/".join(PAYLOAD.relative_to(ROOT).parts)
    overlay.write_text(
        "{\n"
        f'  "productName": "{PRODUCT_NAME}",\n'
        f'  "identifier": "{IDENTIFIER}",\n'
        '  "app": { "windows": [ { "title": '
        f'"{WINDOW_TITLE}"'
        " } ] },\n"
        # 前端只由 step [3] 构建一次：这里把 tauri 自带的 beforeBuildCommand 关掉。
        # 若留着 "pnpm build"，打包阶段会**第二次**重建 dist（vite 会先清空 outDir 再写入）——
        # 期间 mtime 变化触发 tauri-build 重新编译，于是「编译断言过的 exe」与「真正打进
        # 安装器/exe」可能不是同一份；更糟的是若编译恰好读到刚被清空的 dist，会静默产出
        # 不含前端的空壳 exe（装完只有一个网络错误页）。
        '  "build": { "beforeBuildCommand": "", "frontendDist": "../dist" },\n'
        f'  "bundle": {{ "targets": "{BUNDLES}", "resources": {{ "{rel_payload}": "./" }} }}\n'
        "}\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    # MinGW 工具链（crt2.o/系统库）需在 PATH 中——缺失会导致链接期 "cannot find crt2.o"。
    # 注意：必须用 raw string，普通字符串里的 "\b" 会被解释成退格符把路径写坏。
    msys_mingw = r"C:\msys64\mingw64\bin"
    if os.path.isdir(msys_mingw):
        env["PATH"] = msys_mingw + os.pathsep + env.get("PATH", "")
        # 双保险：~/.cargo/bin 下可能存在另一套 MinGW-Builds gcc（无 crt2.o），
        # 显式指定链接器，避免解析到它。
        linker = os.path.join(msys_mingw, "x86_64-w64-mingw32-gcc.exe")
        if os.path.isfile(linker):
            env["CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER"] = linker
    else:
        print(f"    ! 未找到 {msys_mingw}，若链接期报 crt2.o 缺失请安装 MSYS2 mingw-w64-gcc")

    # 关键：风味（productName/identifier/window title + 内嵌前端）由 tauri-build 在**编译期**写入，
    # 而 cargo 不会因为 --config 换了就重跑 build script → 会复用上一个风味的 exe。
    # 必须先清掉本 crate 的构建产物，强制 tauri-build 重跑。
    print("    清理 lawclaw crate 构建缓存（强制 tauri-build 重跑，避免复用旧产物）…")
    subprocess.run(["cargo", "clean", "-p", "lawclaw"], cwd=ROOT / "src-tauri",
                   check=False, shell=True, env=env)

    # ── 先编译，再归档，最后打包 ──
    # 顺序很重要：Tauri 安装器的 resources 是在 **bundle 那一刻**从 payload 目录快照的，
    # 打包完成后再往 payload 里拷文件，就永远进不了安装包（曾导致安装版缺 WebView2Loader.dll、
    # 装完启动报「找不到 WebView2Loader.dll」）。所以先 cargo build 产出 exe 与 DLL，
    # 归档进 payload，再让 tauri build 只做打包（此时 cargo 已是最新，不会重复编译）。
    tauri_cmd = ["pnpm", "tauri", "build", "--config",
                 str(overlay.relative_to(ROOT)).replace("\\", "/")]

    # 预编译必须走 tauri CLI（--no-bundle 只编译不打包）：生产构建的 feature/env 由 CLI 提供。
    # 直接用 `cargo build --release` 会得到一个**开发态** exe——不内嵌前端、转而去找 devUrl
    # （http://localhost:1420），装到客户机就是「无法访问此页面 / localhost 拒绝连接」。
    # 两次调用都带同一份 --config，配置一致 → 打包那次不会触发重新编译。
    print("    预编译（tauri CLI --no-bundle，产出 exe 与 WebView2Loader.dll，供打包前归档）…")
    subprocess.run(tauri_cmd + ["--no-bundle"], cwd=ROOT, check=True, shell=True, env=env)

    # 闸门一：exe 必须内嵌前端。空壳 exe 能起进程、也能拉起后端，唯独 WebView 里是
    # 一个网络错误页——这种失败用「进程活着 + 9876 在听」完全查不出来，必须在这里拦。
    dist_names = _dist_assets()
    _assert_frontend_embedded(_target_exe(), dist_names)

    _archive_runtime_bits()
    archived_hash = _sha256(PAYLOAD / "LawClaw.exe")

    subprocess.run(tauri_cmd, cwd=ROOT, check=True, shell=True, env=env)
    # 打包阶段会再编译一次（CLI 在打包模式下换了构建 env，cargo 判定需要重编），
    # 且打包后还会把 exe patch 进 bundle 类型信息——所以这里重新归档，并**对真正打进
    # 安装器的那份 exe 再断言一次**（安装目录里的 LawClaw.exe 可能来自 resources 里的这份，
    # 也可能来自 bundler 自己拷的那份，两者都必须含前端）。
    # 安装器的 resources 是在**打包那一刻**从 payload 快照的：归档必须发生在这个窗口之前，
    # 或在其后覆盖同一路径——这里两者都做了（打包前归档 + 打包后覆盖）。
    _archive_runtime_bits(quiet=True)
    final_hash = _sha256(PAYLOAD / "LawClaw.exe")
    if final_hash != archived_hash:
        print(f"    · 打包期间 exe 被重新编译（{archived_hash[:12]} → {final_hash[:12]}），"
              "已按打包后的版本重新归档；两份都已断言含前端")
    _assert_frontend_embedded(PAYLOAD / "LawClaw.exe", dist_names, label="payload/LawClaw.exe（打包后）")


def _target_exe() -> Path:
    return ROOT / "src-tauri" / "target" / "release" / "lawclaw.exe"


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dist_assets() -> list:
    """dist 的入口资源名（vite 内容哈希命名）。空 = 前端压根没构建。"""
    assets = ROOT / "dist" / "assets"
    names = sorted(p.name for p in assets.glob("*") if p.suffix in (".js", ".css")) if assets.is_dir() else []
    if not (ROOT / "dist" / "index.html").is_file() or not names:
        raise SystemExit("✗ dist 为空或缺入口资源——前端未构建，产物装出来会是一个空白页")
    return names


def _assert_frontend_embedded(exe: Path, dist_names: list, label: str = "exe") -> None:
    """硬闸：exe 必须内嵌前端资源。

    Tauri 在**编译期**读取 frontendDist 目录、把前端写进二进制。若读的那一刻 dist 是空的
    （例如另一个构建正在重建 dist：vite 会先清空 outDir 再写入），会静默产出一个「空壳 exe」：
    进程起得来、后端也拉得起来，但 WebView 里只有一个网络错误页（ERR_CONNECTION_REFUSED）。
    这种失败在「进程活着 + 9876 在听」这类检查下毫无痕迹，所以必须在构建期拦住。
    """
    if not exe.is_file():
        raise SystemExit(f"✗ 找不到 {exe}（{label}）")
    blob = exe.read_bytes()
    missing = [n for n in dist_names if n.encode("ascii") not in blob]
    if missing:
        raise SystemExit(
            f"✗ {label} 未内嵌前端资源（缺 {missing}）——装出来必然是一个空白错误页，构建终止。\n"
            "  成因通常是编译时 dist 为空或被并发改写（同一仓库同时跑另一个构建/另一个风味）。"
        )
    print(f"    ✓ {label} 已内嵌前端（{len(dist_names)} 个入口资源，sha256 {_sha256(exe)[:12]}）")


def _archive_runtime_bits(quiet: bool = False) -> None:
    """把 exe 与 WebView2Loader.dll 归档进 payload 根。

    二者必须落在 exe 旁边：payload 会整体映射到安装目录与便携目录。
    WebView2Loader.dll 是 GNU 工具链下 exe 的**静态导入依赖**，缺了进程直接报错起不来。
    """
    exe = ROOT / "src-tauri" / "target" / "release" / "lawclaw.exe"
    wv2 = ROOT / "src-tauri" / "target" / "release" / "WebView2Loader.dll"
    if exe.exists():
        shutil.copy2(exe, PAYLOAD / "LawClaw.exe")
        if not quiet:
            print(f"    exe 已归档到 {PAYLOAD.name}/LawClaw.exe")
    if wv2.exists():
        shutil.copy2(wv2, PAYLOAD / "WebView2Loader.dll")
        if not quiet:
            print(f"    WebView2Loader.dll 已归档（{wv2.stat().st_size} bytes，exe 运行时必需）")
    if not quiet and not wv2.exists():
        raise SystemExit("✗ 未找到 target/release/WebView2Loader.dll —— 安装后应用将无法启动，构建终止")


def main():
    global PAYLOAD, BUNDLES
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", default="nsis",
                    help='安装器格式，默认 "nsis"；如需 MSI 传 "nsis,msi" 或 "all"')
    ap.add_argument("--no-smoke", action="store_true", help="跳过发布物冒烟自检")
    ap.add_argument("--portable", action="store_true",
                    help="额外组装 release/portable/（免安装形态：exe + payload 内容）")
    ap.add_argument("--skip-tauri", action="store_true", help="只组装 payload 与运行时（快速验证）")
    ap.add_argument("--skip-runtime", action="store_true", help="跳过运行时构建（已存在时加速）")
    args = ap.parse_args()

    BUNDLES = args.bundles
    PAYLOAD = ROOT / "release" / "payload"

    print(f"═══ 构建 LawClaw 律爪 → {PAYLOAD.relative_to(ROOT)} ═══")
    PAYLOAD.mkdir(parents=True, exist_ok=True)
    step_backend_payload(skip_runtime=args.skip_runtime)
    if not args.skip_runtime:
        step_runtime()
    else:
        print("── [2] 跳过运行时构建（复用既有 runtime；若不存在则产物不可独立运行）──")
    if _payload_python(PAYLOAD / "backend") is None:
        print("    ⚠ payload 内没有捆绑运行时——只能在本机有 Python 的环境运行，不适合交付")
    step_frontend()
    if not args.skip_tauri:
        step_tauri()
    else:
        print("── [4] 跳过 Tauri 构建 ──")
    if args.no_smoke:
        print("── [5] 跳过发布物冒烟（--no-smoke）──")
    else:
        smoke_test_payload()
        purge_smoke_artifacts()
    if args.portable:
        step_portable()
    else:
        print("── [6] 跳过便携目录（加 --portable 生成）──")
    # 自检放最后：它是出货前的最后一道闸
    audit_payload()
    print(f"\n✅ 完成。payload: {PAYLOAD}")
    return 0


def step_portable():
    """组装便携目录（与风味匹配的 exe + payload 内容），供 U 盘/免安装分发。"""
    print("── [6] 组装便携目录（release/portable/）──")
    dst = ROOT / "release" / "portable"
    if dst.exists():
        shutil.rmtree(dst)
    copy_tree(PAYLOAD, dst)
    # 优先用 payload 内归档的 exe（由 step_tauri 写入），避免拷到 target/ 里可能残留的旧 exe。
    exe = PAYLOAD / "LawClaw.exe"
    if not exe.exists():
        exe = ROOT / "src-tauri" / "target" / "release" / "lawclaw.exe"
    if exe.exists():
        shutil.copy2(exe, dst / "LawClaw.exe")
    else:
        print("    ! 未找到 lawclaw.exe，请先跑一次不带 --skip-tauri 的构建")
    for dll in ("WebView2Loader.dll",):
        # 优先取 payload 里归档的那份：安装器就是照它快照的，便携目录要与之同一字节
        src = PAYLOAD / dll
        if not src.exists():
            src = ROOT / "src-tauri" / "target" / "release" / dll
        if src.exists():
            shutil.copy2(src, dst / dll)
    print(f"    ✓ {dst.relative_to(ROOT)}（{_dir_size_mb(dst):.0f} MB）——整目录拷走即可运行")


def purge_smoke_artifacts():
    """清掉冒烟测试自身在 payload 里留下的运行痕迹。

    启动一次包内后端会：写入 .hermes/{state.db,logs,cache,cron,data,memories,...} 与
    .hermes/.env（凭证作用域副本），并为数百个模块生成 __pycache__。
    这些都不能随包分发——所以自检必须排在清理之后。
    """
    be = PAYLOAD / "backend"
    hermes = be / ".hermes"
    if hermes.is_dir():
        # 只保留 build 输入（skills + config.yaml），其余重建为空骨架
        keep = {"skills", "config.yaml"}
        for item in list(hermes.iterdir()):
            if item.name in keep:
                continue
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        for d in HERMES_EMPTY_DIRS:
            (hermes / d).mkdir(exist_ok=True)
    # 清掉冒烟/编译产生的字节码
    n_pyc = 0
    for root, dirs, _files in os.walk(PAYLOAD):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
                n_pyc += 1
    print(f"    已清理冒烟痕迹（.hermes 运行时状态 + {n_pyc} 个 __pycache__）")


def smoke_test_payload():
    """发布前冒烟：用包内捆绑运行时真实启动一次后端，验证能 import、能应答 RPC。

    这是唯一能拦住「打包漏带模块 / 漏带技能」这类问题的检查——静态清单检查不够。
    需要 9876 端口空闲；若被占用（本机开发后端在跑）则跳过并提示。
    """
    print("── [7] 发布物冒烟（启动包内后端）──")
    be = PAYLOAD / "backend"
    py = _payload_python(be)
    if py is None:
        print("    · 无捆绑运行时，跳过")
        return
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", 9876)) == 0:
            print("    ! 9876 已被占用（本机开发后端在跑）→ 跳过；验收前请先停掉它再重跑本步骤")
            return
    proc = subprocess.Popen([str(py), "-u", "main.py", "--ws"], cwd=str(be),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    try:
        # 等端口就绪
        ready = False
        for _ in range(60):
            time.sleep(1)
            with socket.socket() as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", 9876)) == 0:
                    ready = True
                    break
            if proc.poll() is not None:
                break
        if not ready:
            out = (proc.stdout.read() if proc.stdout else "")[-1500:]
            print("    ✗ 后端未能启动：\n" + out)
            return
        client = (
            "import asyncio,json,websockets\n"
            "async def m():\n"
            "    async with websockets.connect('ws://127.0.0.1:9876', ping_interval=None, open_timeout=90) as ws:\n"
            "        await ws.recv()\n"
            "        for meth in ('ping','list_hermes_skills','list_mcp_servers','watchdog_status'):\n"
            "            await ws.send(json.dumps({'jsonrpc':'2.0','id':1,'method':meth,'params':{}}))\n"
            "            while True:\n"
            "                r=json.loads(await ws.recv())\n"
            "                if r.get('id')==1:\n"
            "                    v=r.get('result') or {}\n"
            "                    n=len(v.get('skills',[])) if isinstance(v,dict) and 'skills' in v else (\n"
            "                       len(v.get('servers',[])) if isinstance(v,dict) and 'servers' in v else (\n"
            "                       len(v.get('alerts',[])) if isinstance(v,dict) and 'alerts' in v else v))\n"
            "                    print(f'    {meth}: {n}'); break\n"
            "asyncio.run(m())\n"
        )
        r = subprocess.run([str(py), "-c", client], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        print(r.stdout.rstrip() or r.stderr[-600:])
        ok = ("pong" in (r.stdout or "")) and ("list_hermes_skills" in (r.stdout or ""))
        print("    ✓ 包内后端可启动并应答" if ok else "    ✗ 冒烟未通过，请检查上面的输出")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def audit_payload():
    """发布物自检：确认没有把运行时数据/密钥目录带出去。"""
    print("── [5] 发布物自检 ──")
    be = PAYLOAD / "backend"
    leaks = []
    # 运行时状态（会话/状态库/日志/记忆）
    for pat in ("sessions", "memories", "logs", "state.db", "profiles", "cache"):
        for hit in (be / ".hermes").glob(pat):
            if hit.exists() and (hit.is_file() or any(hit.iterdir())):
                leaks.append(str(hit.relative_to(PAYLOAD)))
    # 密钥
    env_text = (be / ".env").read_text(encoding="utf-8") if (be / ".env").exists() else ""
    if any(l.startswith("OPENAI_API_KEY=") and len(l) > len("OPENAI_API_KEY=") + 4 for l in env_text.splitlines()):
        leaks.append("backend/.env 含 LLM 密钥")
    if any(l.startswith("YUANDIAN_API_KEY=") and len(l) > len("YUANDIAN_API_KEY=") + 4 for l in env_text.splitlines()):
        leaks.append("backend/.env 含元典密钥")
    # 开发笔记（含明文密钥/内部记录）
    for extra in ("AGENTS.md", "scripts", "release"):
        if (PAYLOAD / extra).exists():
            leaks.append(f"顶层多余项 {extra}")
    if leaks:
        print("    ⚠ 发现可疑项，请人工确认：" + "；".join(leaks))
    else:
        print("    ✓ 未携带运行时数据、未携带密钥")
    # 技能是否齐备
    skills = be / ".hermes" / "skills"
    n = len([d for d in skills.iterdir() if d.is_dir()]) if skills.exists() else 0
    print(f"    ✓ 技能目录 {n} 个；payload 体积 {_dir_size_mb(PAYLOAD):.0f} MB")
    # 运行时依赖必须在位：exe 与它的静态导入 DLL 都要落到安装目录/便携目录里，
    # 否则会出现「找不到 WebView2Loader.dll」这类安装后才暴露的启动失败。
    missing = [f for f in ("LawClaw.exe", "WebView2Loader.dll") if not (PAYLOAD / f).exists()]
    if missing:
        print(f"    ✗ 缺少运行时依赖：{missing} —— 安装后应用将无法启动")
    else:
        print("    ✓ 运行时依赖在位（LawClaw.exe + WebView2Loader.dll）")
    # 出货前最后一道闸：EXE 里必须真的装着前端（空壳 exe 是「装完只有一个错误页」的根因）
    if (PAYLOAD / "LawClaw.exe").exists():
        _assert_frontend_embedded(PAYLOAD / "LawClaw.exe", _dist_assets(), label="payload/LawClaw.exe")


def _dir_size_mb(p: Path) -> float:
    total = 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                pass
    return total / 1024 / 1024


if __name__ == "__main__":
    sys.exit(main())
