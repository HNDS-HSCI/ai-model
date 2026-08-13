use std::time::Duration;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::process::Command;

#[derive(Debug, Error)]
pub enum SandboxError {
    #[error("Execution timed out after {0:?}")]
    Timeout(Duration),

    #[error("Subprocess execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Security policy violation: {0}")]
    SecurityViolation(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallRequest {
    pub tool_name: String,
    pub command_line: String,
    pub timeout_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

pub struct ToolSandbox;

impl ToolSandbox {
    pub async fn execute_tool(
        request: ToolCallRequest,
    ) -> Result<ToolCallResult, SandboxError> {
        // Enforce TIA-1 Process Isolation Security Guardrails
        if request.command_line.contains("rm -rf") || request.command_line.contains("format") {
            return Err(SandboxError::SecurityViolation(
                "Restricted command pattern detected".to_string(),
            ));
        }

        let timeout_duration = Duration::from_secs(request.timeout_seconds);

        let mut child = Command::new("cmd")
            .args(&["/C", &request.command_line])
            .output();

        match tokio::time::timeout(timeout_duration, child).await {
            Ok(Ok(output)) => Ok(ToolCallResult {
                stdout: String::from_utf8_lossy(&output.stdout).to_string(),
                stderr: String::from_utf8_lossy(&output.stderr).to_string(),
                exit_code: output.status.code().unwrap_or(-1),
            }),
            Ok(Err(err)) => Err(SandboxError::ExecutionFailed(err.to_string())),
            Err(_) => Err(SandboxError::Timeout(timeout_duration)),
        }
    }
}
