# -*- coding: utf-8 -*-
"""LawClaw 发行构建脚本（双风味）。

两种交付物由同一套代码产出，差别只在"首启是否有演示数据"与"是否携带密钥"：

  --flavor demo   演示版：首启灌入演示案件数据（客户当面/远程演示用）；
                  默认不带任何密钥，可选 --with-llm-key / --with-yuandian-key 注入。
  --flavor clean  客户版：首启空台账、无演示数据、无任何密钥，客户自行配置。

产物形态（每风味一套，互不覆盖）：
  release/payload-<flavor>/
  ├── LawClaw.exe              ← Tauri 构建（--skip-tauri 时缺省）
  ├── run_agent.py, hermes_*.py, utils.py, agent/, tools/, providers/, ...  ← Hermes 底座
  └── backend/
      ├── main.py, doc_intel.py, config.yaml, requirements-runtime.txt
      ├── runtime/             ← uv venv（捆绑 Python 运行时）
      ├── .hermes/             ← 干净首启：skills/ + config.yaml + 空骨架（无会话/密钥数据）
      └── .env                 ← LLM key 留空（首启向导填写）；元典 key 默认留空

用法：
  python scripts/build_release.py --flavor demo                 # 演示版（全量，含安装器）
  python scripts/build_release.py --flavor clean                # 客户版
  python scripts/build_release.py --flavor demo --skip-tauri    # 只组 payload（快速验证）
  python scripts/build_release.py --flavor demo --with-llm-key --with-yuandian-key
                                                                # 演示机免配置（⚠ 产物含真实密钥）

⚠ 密钥警示：带 --with-*-key 的产物内含真实密钥，仅供你自己的演示机使用，
  绝不能把该安装包/目录交给客户或放到公开渠道。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "release" / "payload"          # 由 main() 按 flavor 重定向
BACKEND_SRC = ROOT / "backend"

# 风味元数据：安装标识分开 → 两种版本可并存且 localStorage（演示数据）互不污染
FLAVORS = {
    "demo": {
        "product_name": "LawClaw-Demo",
        "identifier": "com.lawclaw.demo",
        "window_title": "LawClaw 律爪 — 演示版（含演示数据）",
        "label": "演示版",
    },
    "clean": {
        "product_name": "LawClaw",
        "identifier": "com.lawclaw.app",
        "window_title": "LawClaw 律爪 — 律师智能体",
        "label": "客户版",
    },
}

# 默认 LLM 端点（OpenAI 兼容协议；演示机可在向导里改）
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-flash"

# 由 main() 赋值的全局开关
FLAVOR = "demo"
WITH_LLM_KEY = False
WITH_YD_KEY = False
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

    # 发行物标识：一眼看出这是哪个风味的包，以及是否含密钥
    from datetime import datetime
    meta = FLAVORS[FLAVOR]
    (PAYLOAD / "BUILD_INFO.txt").write_text(
        f"LawClaw 律爪 发行物信息\n"
        f"======================\n"
        f"风味(flavor)   : {FLAVOR}（{meta['label']}）\n"
        f"产品名         : {meta['product_name']}\n"
        f"安装标识       : {meta['identifier']}\n"
        f"首启数据       : {'含虚构演示案件数据' if FLAVOR == 'demo' else '空台账（无演示数据）'}\n"
        f"安装器格式     : {BUNDLES}\n"
        f"注入密钥       : LLM={'是（含真实密钥，勿外传）' if WITH_LLM_KEY else '否'}"
        f" / 元典={'是（含真实密钥，勿外传）' if WITH_YD_KEY else '否'}\n"
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
    keys = []
    keys.append("LLM key " + ("已注入（⚠ 含真实密钥）" if WITH_LLM_KEY else "留空（首启向导填写）"))
    keys.append("元典 key " + ("已注入（⚠ 含真实密钥）" if WITH_YD_KEY else "留空"))
    print(f"    payload/backend 就绪（.hermes skills 携带；{ '；'.join(keys) }）")


def _read_dev_env() -> dict:
    """读开发机 backend/.env（仅用于 --with-*-key 的显式注入）。"""
    out = {}
    dev_env = BACKEND_SRC / ".env"
    if dev_env.exists():
        for line in dev_env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def _env_template() -> str:
    """生成 payload 的 .env：默认不含任何密钥；密钥只在显式开关下注入。"""
    dev = _read_dev_env()
    llm_key = dev.get("OPENAI_API_KEY", "") if WITH_LLM_KEY else ""
    base_url = (dev.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL) if WITH_LLM_KEY else DEFAULT_BASE_URL
    model = (dev.get("LAWCLAW_MODEL") or DEFAULT_MODEL) if WITH_LLM_KEY else DEFAULT_MODEL
    yd_key = dev.get("YUANDIAN_API_KEY", "") if WITH_YD_KEY else ""
    return (
        f"# LawClaw 环境变量（风味：{FLAVOR}）\n"
        "# LLM 凭证：可在应用内「配置」或首启向导填写；此处留空即由用户在界面配置。\n"
        f"OPENAI_API_KEY={llm_key}\n"
        f"OPENAI_BASE_URL={base_url}\n"
        f"LAWCLAW_MODEL={model}\n"
        "# 元典开放平台（法律检索数据源）。留空则检索功能提示未配置，需填入自己的 Key。\n"
        f"YUANDIAN_API_KEY={yd_key}\n"
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
    print(f"── [3] 前端构建（VITE_LAWCLAW_FLAVOR={FLAVOR}）──")
    env = dict(os.environ)
    env["VITE_LAWCLAW_FLAVOR"] = FLAVOR
    # vue-tsc + vite 在大项目上容易撞 V8 默认堆上限（表现为 node::OnFatalError / exit 134），
    # 尤其在同时跑着 vite dev server 时。显式抬高堆上限，避免误判为构建失败。
    env["NODE_OPTIONS"] = (env.get("NODE_OPTIONS", "") + " --max-old-space-size=4096").strip()
    subprocess.run(["pnpm", "build"], cwd=ROOT, check=True, shell=True, env=env)


def step_tauri():
    print(f"── [4] Tauri release 构建（{FLAVORS[FLAVOR]['label']}）──")
    # 发行配置 overlay：把本风味的 payload 作为资源打进安装器，
    # 并用独立 productName/identifier —— 演示版与客户版可并存且 localStorage 互不污染。
    meta = FLAVORS[FLAVOR]
    overlay = ROOT / "release" / f"tauri.release.{FLAVOR}.conf.json"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    rel_payload = "../" + "/".join(PAYLOAD.relative_to(ROOT).parts)
    overlay.write_text(
        "{\n"
        f'  "productName": "{meta["product_name"]}",\n'
        f'  "identifier": "{meta["identifier"]}",\n'
        '  "app": { "windows": [ { "title": '
        f'"{meta["window_title"]}"'
        " } ] },\n"
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
    print("    清理 lawclaw crate 构建缓存（确保 tauri-build 重跑，否则会串风味）…")
    subprocess.run(["cargo", "clean", "-p", "lawclaw"], cwd=ROOT / "src-tauri",
                   check=False, shell=True, env=env)

    subprocess.run(
        ["pnpm", "tauri", "build", "--config", str(overlay.relative_to(ROOT)).replace("\\", "/")],
        cwd=ROOT, check=True, shell=True, env=env,
    )
    # 把刚构建的 exe 直接放进本风味 payload：便携目录/交付时不再靠 target/ 里的“当前 exe”，
    # 从根上消除拷错风味 exe 的可能。
    exe = ROOT / "src-tauri" / "target" / "release" / "lawclaw.exe"
    if exe.exists():
        shutil.copy2(exe, PAYLOAD / "LawClaw.exe")
        print(f"    exe 已归档到 {PAYLOAD.name}/LawClaw.exe（与风味绑定）")


def main():
    global PAYLOAD, FLAVOR, WITH_LLM_KEY, WITH_YD_KEY, BUNDLES
    ap = argparse.ArgumentParser()
    ap.add_argument("--flavor", choices=sorted(FLAVORS), default="demo",
                    help="demo=演示版（含演示数据）；clean=客户版（空台账、无密钥）")
    ap.add_argument("--bundles", default="nsis",
                    help='安装器格式，默认 "nsis"；如需 MSI 传 "nsis,msi" 或 "all"')
    ap.add_argument("--no-smoke", action="store_true", help="跳过发布物冒烟自检")
    ap.add_argument("--portable", action="store_true",
                    help="额外组装 release/portable-<flavor>/（免安装形态，与风味匹配的 exe + payload）")
    ap.add_argument("--skip-tauri", action="store_true", help="只组装 payload 与运行时（快速验证）")
    ap.add_argument("--skip-runtime", action="store_true", help="跳过运行时构建（已存在时加速）")
    ap.add_argument("--with-llm-key", action="store_true",
                    help="⚠ 把开发机 backend/.env 的 LLM 凭证写进产物（仅演示机自用）")
    ap.add_argument("--with-yuandian-key", action="store_true",
                    help="⚠ 把开发机的元典 API Key 写进产物（仅演示机自用）")
    args = ap.parse_args()

    FLAVOR = args.flavor
    BUNDLES = args.bundles
    WITH_LLM_KEY = args.with_llm_key
    WITH_YD_KEY = args.with_yuandian_key
    if FLAVOR == "clean" and (WITH_LLM_KEY or WITH_YD_KEY):
        print("✗ 客户版不接受 --with-*-key（客户版必须不含任何密钥）", file=sys.stderr)
        return 2
    PAYLOAD = ROOT / "release" / f"payload-{FLAVOR}"

    print(f"═══ 构建 {FLAVORS[FLAVOR]['label']}（flavor={FLAVOR}）→ {PAYLOAD.relative_to(ROOT)} ═══")
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
    print(f"── [6] 组装便携目录（portable-{FLAVOR}）──")
    dst = ROOT / "release" / f"portable-{FLAVOR}"
    if dst.exists():
        shutil.rmtree(dst)
    copy_tree(PAYLOAD, dst)
    # 优先用 payload 内归档的、与风味绑定的 exe（由 step_tauri 写入），
    # 避免拷到 target/ 里残留的其他风味 exe。
    exe = PAYLOAD / "LawClaw.exe"
    if not exe.exists():
        exe = ROOT / "src-tauri" / "target" / "release" / "lawclaw.exe"
    if exe.exists():
        shutil.copy2(exe, dst / "LawClaw.exe")
    else:
        print("    ! 未找到 lawclaw.exe，请先跑一次不带 --skip-tauri 的构建")
    for dll in ("WebView2Loader.dll",):
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
