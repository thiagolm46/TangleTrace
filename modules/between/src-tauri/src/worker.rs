//! Scientific process supervisor. One request at a time; no sockets.
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc::{self, Receiver},
    time::Duration,
};

pub struct Worker {
    child: Child,
    input: ChildStdin,
    output: Receiver<Result<String, String>>,
    sequence: u64,
    failed: bool,
    pub workspace: PathBuf,
}

impl Worker {
    pub fn failed(&self) -> bool {
        self.failed
    }

    pub fn start(workspace: &Path) -> Result<Self, String> {
        std::fs::create_dir_all(workspace)
            .map_err(|e| format!("Could not open workspace: {e}"))?;
        let workspace = workspace.canonicalize().map_err(|e| e.to_string())?;
        let executable = std::env::current_exe().map_err(|e| e.to_string())?;
        let packaged = executable
            .parent()
            .ok_or("Executable folder unavailable")?
            .join("worker")
            .join(if cfg!(windows) {
                "discord-annotation-worker.exe"
            } else {
                "discord-annotation-worker"
            });
        let mut command = if packaged.is_file() {
            Command::new(packaged)
        } else {
            let project = std::env::var_os("DISCORD_ANNOTATOR_PROJECT")
                .map(PathBuf::from).ok_or("Local processor is missing. Run Start-Desktop.ps1 from source or Build-Desktop.ps1 to prepare the complete application.")?;
            let python = std::env::var_os("DISCORD_ANNOTATOR_PYTHON")
                .ok_or("Set DISCORD_ANNOTATOR_PYTHON or use Start-Desktop.ps1.")?;
            let mut cmd = Command::new(python);
            cmd.current_dir(project).args(["-u", "-m", "app.worker"]);
            cmd
        };
        command.arg("--workspace").arg(&workspace);
        if let Some(source) = std::env::var_os("DISCORD_ANNOTATOR_SOURCE") {
            command.arg("--source").arg(source);
        }
        command
            .env("PYTHONUTF8", "1")
            .env("PYTHONUNBUFFERED", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let mut child = command
            .spawn()
            .map_err(|e| format!("Could not start the local processor: {e}"))?;
        let input = child.stdin.take().ok_or("Worker stdin unavailable")?;
        let stdout = child.stdout.take().ok_or("Worker stdout unavailable")?;
        let (sender, output) = mpsc::sync_channel(2);
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                if sender.send(line.map_err(|e| e.to_string())).is_err() {
                    break;
                }
            }
        });
        let mut worker = Self {
            child,
            input,
            output,
            sequence: 0,
            failed: false,
            workspace,
        };
        let config = worker.request("config", json!({}))?;
        if config["protocol_version"] != 1 {
            return Err("Incompatible local processor version.".into());
        }
        Ok(worker)
    }

    pub fn request(&mut self, method: &str, params: Value) -> Result<Value, String> {
        if self.failed {
            return Err("The processor stopped unexpectedly. Reopen the application and check the last saved decision before continuing.".into());
        }
        if !params.is_object() {
            return Err("Invalid parameters.".into());
        }
        self.sequence += 1;
        let mut payload =
            serde_json::to_vec(&json!({"id": self.sequence, "method": method, "params": params}))
                .map_err(|e| e.to_string())?;
        if payload.len() >= 2 * 1024 * 1024 {
            return Err("Request exceeds the local limit.".into());
        }
        payload.push(b'\n');
        if self
            .input
            .write_all(&payload)
            .and_then(|_| self.input.flush())
            .is_err()
        {
            self.failed = true;
            return Err(
                "The internal connection to the processor closed. Reopen the application.".into(),
            );
        }
        let line = match self.output.recv_timeout(Duration::from_secs(300)) {
            Ok(Ok(line)) => line,
            _ => {
                self.failed = true;
                let _ = self.child.kill();
                return Err("The local processor stopped or exceeded five minutes. Reopen the tool and check the saved state. The operation was not retried automatically.".into());
            }
        };
        let response: Value = serde_json::from_str(&line).map_err(|_| {
            self.failed = true;
            "Invalid response from the local processor. Reopen the application.".to_string()
        })?;
        if response["id"].as_u64() != Some(self.sequence) {
            self.failed = true;
            return Err("Out-of-order internal response. Reopen the application.".into());
        }
        if response["ok"] != true {
            return Err(response["error"]["message"]
                .as_str()
                .unwrap_or("Local processing failed.")
                .to_owned());
        }
        Ok(response["result"].clone())
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        // Normal shutdown already completed transactions; closing the window also
        // stops the child process to avoid orphans and persistent locks.
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
