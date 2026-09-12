// LawClaw · Tauri 2 入口文件
//
// 命令契约（前端 invoke 必须严格匹配参数名）：
//   invoke('send_notification',              { title, body })
//   invoke('schedule_notification',          { id, fire_at_unix, title, body, matter_id })
//   invoke('cancel_notification',            { id })
//   invoke('list_scheduled_notifications',   {})
//   invoke('request_notification_permission', {})
//
// 前端调用参数名必须全部使用 snake_case（与 Rust #[tauri::command] 参数名 1:1 对应）

use tauri::Manager;
use tauri_plugin_notification::NotificationExt;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use std::sync::Mutex;
use std::collections::HashMap;

/// 已调度通知的元数据
#[derive(Clone, serde::Serialize)]
pub struct ScheduledNotification {
    pub id: String,
    pub fire_at_unix: u64,
    pub title: String,
    pub body: String,
    pub matter_id: Option<String>,
}

/// 全局调度表：Mutex 包裹允许多线程访问
static SCHEDULED_NOTIFICATIONS: Mutex<Option<HashMap<String, ScheduledNotification>>> =
    Mutex::new(None);

fn with_lock<F, R>(f: F) -> Result<R, String>
where
    F: FnOnce(&mut Option<HashMap<String, ScheduledNotification>>) -> R,
{
    let mut guard = SCHEDULED_NOTIFICATIONS
        .lock()
        .map_err(|e| format!("通知调度表锁失败: {}", e))?;
    Ok(f(&mut guard))
}

fn ensure_map(
    opt: &mut Option<HashMap<String, ScheduledNotification>>,
) -> &mut HashMap<String, ScheduledNotification> {
    if opt.is_none() {
        *opt = Some(HashMap::new());
    }
    opt.as_mut().unwrap()
}

// ─────────────────────────────────────────────
//  Tauri 命令
// ─────────────────────────────────────────────

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to LawClaw!", name)
}

#[tauri::command]
fn get_backend_info() -> String {
    serde_json::json!({
        "name": "LawClaw",
        "version": "0.1.0",
        "description": "LawClaw 律爪 — 律师智能体"
    })
    .to_string()
}

/// 立即发送系统通知
#[tauri::command]
fn send_notification(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| format!("通知发送失败: {}", e))
}

/// 定时通知：在指定 Unix 秒触发
#[tauri::command]
async fn schedule_notification(
    app: tauri::AppHandle,
    id: String,
    fire_at_unix: u64,
    title: String,
    body: String,
    matter_id: Option<String>,
) -> Result<(), String> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_secs();

    // 1. 先登记到调度表（即使 delay=0 也登记，方便 list 查询）
    with_lock(|opt| {
        let map = ensure_map(opt);
        map.insert(
            id.clone(),
            ScheduledNotification {
                id: id.clone(),
                fire_at_unix,
                title: title.clone(),
                body: body.clone(),
                matter_id: matter_id.clone(),
            },
        );
    })?;

    // 2. 计算延迟
    let delay_secs = if fire_at_unix > now {
        fire_at_unix - now
    } else {
        0
    };

    // 3. 立即触发？直接 send
    if delay_secs == 0 {
        return send_notification(app, title, body);
    }

    // 4. 异步等待触发
    let app_clone = app.clone();
    let id_clone = id.clone();
    let title_clone = title.clone();
    let body_clone = body.clone();

    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(Duration::from_secs(delay_secs)).await;

        // 再次检查是否被取消
        let still_scheduled = with_lock(|opt| {
            opt.as_ref()
                .map(|m| m.contains_key(&id_clone))
                .unwrap_or(false)
        })
        .unwrap_or(false);

        if !still_scheduled {
            return;
        }

        // 发送通知
        let _ = app_clone
            .notification()
            .builder()
            .title(&title_clone)
            .body(&body_clone)
            .show();

        // 发送成功后移除
        let _ = with_lock(|opt| {
            if let Some(map) = opt.as_mut() {
                map.remove(&id_clone);
            }
        });
    });

    Ok(())
}

/// 取消一条定时通知
#[tauri::command]
fn cancel_notification(id: String) -> Result<bool, String> {
    with_lock(|opt| {
        opt.as_mut()
            .map(|map| map.remove(&id).is_some())
            .unwrap_or(false)
    })
}

/// 列出所有待触发的通知
#[tauri::command]
fn list_scheduled_notifications() -> Result<Vec<ScheduledNotification>, String> {
    with_lock(|opt| {
        opt.as_ref()
            .map(|map| map.values().cloned().collect::<Vec<_>>())
            .unwrap_or_default()
    })
}

/// 请求通知权限（Tauri 在首次 show() 时 Win10/11 会弹授权框）
#[tauri::command]
fn request_notification_permission(app: tauri::AppHandle) -> Result<bool, String> {
    match app
        .notification()
        .builder()
        .title("LawClaw 律爪")
        .body("通知权限已启用，您将收到期限提醒")
        .show()
    {
        Ok(_) => Ok(true),
        Err(e) => Err(format!("通知权限请求失败: {}", e)),
    }
}

// ─────────────────────────────────────────────
//  入口
// ─────────────────────────────────────────────
//  后端进程生命周期（借鉴 openmemory-manager 引用计数自启停模式）
//  · 启动时：9876 端口已有后端（用户手动启动）→ 不重复拉起
//  · 全部窗口关闭 → 递减归零 → 杀掉后端进程
//  · 后端以 --ws 模式运行（stdio-EOF 即退出的缺陷规避）
// ─────────────────────────────────────────────

use std::process::{Child, Command};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

static BACKEND_CHILD: Mutex<Option<Child>> = Mutex::new(None);
static OPEN_WINDOWS: AtomicUsize = AtomicUsize::new(0);
/// 退出中：supervisor 心跳据此停手，避免「关窗杀后端 → 心跳又拉起来」。
static SHUTDOWN: AtomicBool = AtomicBool::new(false);
static SUPERVISOR_STARTED: AtomicBool = AtomicBool::new(false);

fn backend_port_free() -> bool {
    std::net::TcpStream::connect("127.0.0.1:9876").is_err()
}

fn resolve_backend_dir() -> Option<std::path::PathBuf> {
    // ① 显式环境变量（开发/测试接管）
    if let Ok(dir) = std::env::var("LAWCLAW_BACKEND_DIR") {
        let p = std::path::PathBuf::from(dir);
        if p.join("main.py").exists() {
            return Some(p);
        }
    }
    // ② 交付形态：exe 同级的 backend/ —— 永远优先。
    //    曾经把 dev 路径排在前面，结果在开发机上安装版会跑去跑开发树里的后端：
    //    既让「安装版是否真能跑」的验证失去意义，也依赖编译机上的绝对路径。
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let p = dir.join("backend");
            if p.join("main.py").exists() {
                return Some(p);
            }
        }
    }
    // ③ dev：Cargo 清单目录的上级/backend（仅 debug 构建；release 里不保留编译机路径）
    #[cfg(debug_assertions)]
    {
        let dev_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()?
            .join("backend");
        if dev_dir.join("main.py").exists() {
            return Some(dev_dir);
        }
    }
    None
}

/// 追加一行启动器日志（exe 同级的 launcher.log）。
///
/// GUI 进程没有控制台，`eprintln!` 等于丢进黑洞——「后端引擎未启动」这类问题因此无从排查。
/// 日志本身是辅助手段，任何失败都静默，绝不影响启动。
fn log_line(msg: &str) {
    use std::io::Write;
    let Ok(exe) = std::env::current_exe() else { return };
    let Some(dir) = exe.parent() else { return };
    let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("launcher.log"))
    else {
        return;
    };
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let _ = writeln!(f, "[{ts}] {msg}");
}

/// 回收已退出的子进程句柄（否则 guard.is_some() 会一直挡着不让重启）。
fn reap_child() -> Option<u32> {
    let Ok(mut guard) = BACKEND_CHILD.lock() else { return None };
    if let Some(child) = guard.as_mut() {
        match child.try_wait() {
            Ok(Some(status)) => {
                let id = child.id();
                *guard = None;
                log_line(&format!("backend exited: pid={id} status={status}"));
                return Some(id);
            }
            Ok(None) => {}
            Err(e) => log_line(&format!("backend try_wait failed: {e}")),
        }
    }
    None
}

fn spawn_backend() {
    let mut guard = match BACKEND_CHILD.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    if guard.is_some() {
        return; // 已在跑
    }
    if !backend_port_free() {
        // 端口已被占用：可能是用户自己起的后端，也可能只是别人临时占着。
        // 这里不抢，由 supervisor 循环在端口释放后补拉（见 ensure_backend）。
        return;
    }
    let dir = match resolve_backend_dir() {
        Some(d) => d,
        None => {
            log_line("no backend/main.py found (set LAWCLAW_BACKEND_DIR)");
            return;
        }
    };
    // Python 解析顺序：捆绑运行时（新布局 runtime/python.exe）→ 旧布局（venv）
    // → 环境变量 → PATH。
    // 新布局是自带标准库与 python3xx.dll 的独立解释器（可重定位），客户机无需安装 Python；
    // 旧布局是 venv，依赖开发机上的基础解释器，仅作兼容保留。
    let bundled_standalone = dir.join("runtime").join("python.exe");
    let bundled_venv = dir.join("runtime").join("Scripts").join("python.exe");
    let python = if bundled_standalone.exists() {
        bundled_standalone.to_string_lossy().into_owned()
    } else if bundled_venv.exists() {
        bundled_venv.to_string_lossy().into_owned()
    } else {
        std::env::var("LAWCLAW_PYTHON").unwrap_or_else(|_| "python".into())
    };
    let mut cmd = Command::new(python.clone());
    cmd.arg("main.py").arg("--ws").current_dir(&dir);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    match cmd.spawn() {
        Ok(child) => {
            log_line(&format!(
                "backend spawned: pid={} python={} dir={}",
                child.id(),
                python,
                dir.display()
            ));
            *guard = Some(child);
        }
        Err(e) => log_line(&format!("backend spawn FAILED: {e} (python={python})")),
    }
}

/// 保证「9876 上有一个后端」——启动时端口被别人占着、或我们拉起的后端中途退出，
/// 都能自愈。
///
/// 之前的实现只在 setup() 里尝试一次：若那一刻 9876 被占用（例如用户自己起了后端、
/// 或另一个进程临时占着），应用就再也不拉后端了——端口随占用者退出而空出后，界面会一直
/// 停在「后端引擎未启动」，只能重启应用。这里用后台心跳把这个洞补上。
fn ensure_backend() {
    if !backend_port_free() {
        reap_child();
        return; // 有后端在听 → 不干预（外部后端同样接受）
    }
    reap_child();
    spawn_backend();
}

fn start_supervisor() {
    if SUPERVISOR_STARTED.swap(true, Ordering::SeqCst) {
        return; // 只起一条
    }
    std::thread::spawn(|| loop {
        std::thread::sleep(Duration::from_secs(3));
        if SHUTDOWN.load(Ordering::SeqCst) {
            return;
        }
        ensure_backend();
    });
}

fn kill_backend() {
    SHUTDOWN.store(true, Ordering::SeqCst);
    if let Ok(mut guard) = BACKEND_CHILD.lock() {
        if let Some(child) = guard.as_mut() {
            let _ = child.kill();
            let _ = child.wait();
            log_line("backend stopped (app shutting down)");
        }
        *guard = None;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            get_backend_info,
            send_notification,
            schedule_notification,
            cancel_notification,
            list_scheduled_notifications,
            request_notification_permission,
        ])
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.open_devtools();
                }
            }
            // 引用计数：登记窗口数并拉起后端（幂等——已有后端监听 9876 则跳过）
            OPEN_WINDOWS.store(app.webview_windows().len(), Ordering::SeqCst);
            SHUTDOWN.store(false, Ordering::SeqCst);
            log_line("app started");
            spawn_backend();
            // 心跳兜底：端口当时被占、或后端中途退出，都能自愈
            start_supervisor();
            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // 引用计数递减：归零（最后一个窗口关闭）→ 停止后端
                let n = OPEN_WINDOWS.fetch_sub(1, Ordering::SeqCst);
                if n <= 1 {
                    kill_backend();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("启动 LawClaw 失败")
        .run(|_app, event| {
            // 应用整体退出兜底清理（窗口 Destroyed 未触发时，如进程被杀前）
            if let tauri::RunEvent::Exit = event {
                kill_backend();
            }
        });
}
