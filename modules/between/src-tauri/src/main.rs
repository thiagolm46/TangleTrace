#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod worker;

use serde_json::{json, Value};
use std::{
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
};
use tauri::{Emitter, Manager};
use worker::Worker;

struct Desktop {
    worker: Mutex<Option<Worker>>,
    workspace: Mutex<PathBuf>,
    settings_file: PathBuf,
    closing: AtomicBool,
    frontend_ready: AtomicBool,
}

const METHODS: &[&str] = &[
    "config",
    "imports",
    "windows",
    "state",
    "sessions",
    "compare",
    "history",
    "job",
    "import",
    "demo",
    "open_session",
    "cursor",
    "draft",
    "discard_draft",
    "confirm",
    "undo",
    "redo",
    "review_component",
    "review_interval",
    "export",
    "backup",
    "ensure_idle",
];

#[tauri::command]
async fn backend_request(
    app: tauri::AppHandle,
    method: String,
    params: Value,
) -> Result<Value, String> {
    if !METHODS.contains(&method.as_str()) {
        return Err("Command is not allowed.".into());
    }
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<Desktop>();
        state.frontend_ready.store(true, Ordering::SeqCst);
        if state.closing.load(Ordering::SeqCst) {
            return Err("The application is shutting down.".into());
        }
        let mut slot = state
            .worker
            .lock()
            .map_err(|_| "Processor unavailable")?;
        if slot.is_none() {
            let path = state
                .workspace
                .lock()
                .map_err(|_| "Workspace unavailable")?
                .clone();
            *slot = Some(Worker::start(&path)?);
        }
        slot.as_mut()
            .ok_or("Processor unavailable")?
            .request(&method, params)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn pick_path(kind: String) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let dialog = rfd::FileDialog::new();
        let selected = match kind.as_str() {
            "sample_folder" => dialog.set_title("Sampling folder").pick_folder(),
            "sample_file" => dialog
                .set_title("Window CSV or sample Parquet")
                .add_filter("Sample", &["csv", "parquet"])
                .pick_file(),
            "workspace" => dialog
                .set_title("Local folder for database, backups, and results")
                .pick_folder(),
            _ => return Err("Unknown file picker type.".into()),
        };
        Ok(selected.map(|p| p.to_string_lossy().into_owned()))
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn switch_workspace(app: tauri::AppHandle, path: String) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let chosen = PathBuf::from(path);
        if !chosen.is_dir() {
            return Err("Select an existing folder.".into());
        }
        let chosen = chosen.canonicalize().map_err(|e| e.to_string())?;
        let state = app.state::<Desktop>();
        let mut slot = state
            .worker
            .lock()
            .map_err(|_| "Processor unavailable")?;
        if let Some(old) = slot.as_mut() {
            old.request("ensure_idle", json!({}))?;
            if old.workspace == chosen {
                return old.request("config", json!({}));
            }
        }
        // Switch only after confirming that the new worker can open the workspace.
        let mut next = Worker::start(&chosen)?;
        let config = next.request("config", json!({}))?;
        let settings =
            serde_json::to_vec_pretty(&json!({"workspace": chosen})).map_err(|e| e.to_string())?;
        let pending = state.settings_file.with_extension("tmp");
        std::fs::write(&pending, settings).map_err(|e| e.to_string())?;
        std::fs::rename(&pending, &state.settings_file).map_err(|e| e.to_string())?;
        *state.workspace.lock().map_err(|_| "Workspace unavailable")? = chosen;
        *slot = Some(next);
        Ok(config)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn open_local_folder(app: tauri::AppHandle, path: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<Desktop>();
        let root = state
            .workspace
            .lock()
            .map_err(|_| "Workspace unavailable")?
            .canonicalize()
            .map_err(|e| e.to_string())?;
        let target = PathBuf::from(path)
            .canonicalize()
            .map_err(|_| "The folder does not exist yet. Export data or create a backup first.")?;
        if !target.is_dir() || !target.starts_with(&root) {
            return Err("Only folders inside this workspace can be opened.".into());
        }
        #[cfg(windows)]
        let mut command = std::process::Command::new("explorer.exe");
        #[cfg(target_os = "macos")]
        let mut command = std::process::Command::new("open");
        #[cfg(all(unix, not(target_os = "macos")))]
        let mut command = std::process::Command::new("xdg-open");
        command.arg(target).spawn().map_err(|e| e.to_string())?;
        Ok(())
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn finish_close(app: tauri::AppHandle, force: bool) -> Result<(), String> {
    let handle = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let state = handle.state::<Desktop>();
        let mut slot = state
            .worker
            .lock()
            .map_err(|_| "Processor unavailable")?;
        if let Some(worker) = slot.as_mut() {
            if !force && !worker.failed() {
                worker.request("shutdown", json!({}))?;
            }
        }
        state.closing.store(true, Ordering::SeqCst);
        slot.take();
        Ok::<(), String>(())
    })
    .await
    .map_err(|e| e.to_string())??;
    app.exit(0);
    Ok(())
}

fn main() {
    // Diagnose without opening a window or importing real samples.
    if std::env::args().any(|a| a == "--diagnose") {
        let result = (|| {
            let path = std::env::var_os("DISCORD_ANNOTATOR_WORKSPACE")
                .map(PathBuf::from)
                .ok_or("Set DISCORD_ANNOTATOR_WORKSPACE for diagnostics.")?;
            let mut worker = Worker::start(&path)?;
            let config = worker.request("config", json!({}))?;
            worker.request("shutdown", json!({}))?;
            Ok::<Value, String>(config)
        })();
        match result {
            Ok(config) => println!("{}", config),
            Err(error) => {
                eprintln!("{}", error);
                std::process::exit(1);
            }
        }
        return;
    }
    tauri::Builder::default()
        .setup(|app| {
            let config_dir = app.path().app_config_dir()?;
            std::fs::create_dir_all(&config_dir)?;
            let settings_file = config_dir.join("desktop.json");
            let saved: Option<Value> = std::fs::read(&settings_file)
                .ok()
                .and_then(|b| serde_json::from_slice(&b).ok());
            let workspace = std::env::var_os("DISCORD_ANNOTATOR_WORKSPACE")
                .map(PathBuf::from)
                .or_else(|| saved.and_then(|v| v["workspace"].as_str().map(PathBuf::from)))
                .unwrap_or(app.path().app_local_data_dir()?.join("workspace"));
            app.manage(Desktop {
                worker: Mutex::new(None),
                workspace: Mutex::new(workspace),
                settings_file,
                closing: AtomicBool::new(false),
                frontend_ready: AtomicBool::new(false),
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let state = window.state::<Desktop>();
                if state.frontend_ready.load(Ordering::SeqCst)
                    && !state.closing.load(Ordering::SeqCst)
                {
                    api.prevent_close();
                    let _ = window.emit("desktop-close-requested", ());
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            backend_request,
            pick_path,
            switch_workspace,
            open_local_folder,
            finish_close
        ])
        .run(tauri::generate_context!())
        .expect("Could not open the desktop window");
}
