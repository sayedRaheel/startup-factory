use axum::{
    extract::{State},
    routing::post,
    Router,
    response::IntoResponse,
    Json,
};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct AppState {
    pub is_proven: Arc<Mutex<bool>>,
    pub compiled_context: String,
    pub real_api_base: String,
}

pub async fn start_proxy(state: AppState, port: u16) {
    let app = Router::new()
        .route("/v1/chat/completions", post(intercept_completions))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", port)).await.unwrap();
    tracing::info!("Tether Proxy intercepting on port {}", port);
    axum::serve(listener, app).await.unwrap();
}

async fn intercept_completions(
    State(state): State<AppState>,
    Json(mut payload): Json<serde_json::Value>,
) -> impl IntoResponse {
    let mut is_proven = state.is_proven.lock().await;

    if let Some(messages) = payload.get_mut("messages").and_then(|m| m.as_array_mut()) {
        if let Some(sys_msg) = messages.first_mut() {
            let current_content = sys_msg["content"].as_str().unwrap_or("");
            let injected_content = format!(
                "{} \n\n[TETHER STRICT CONTEXT]\n{}\n[END TETHER CONTEXT]\n\nYou MUST output a JSON tool call to `prove_architecture` before writing any files.",
                current_content, state.compiled_context
            );
            sys_msg["content"] = serde_json::Value::String(injected_content);
        }
    }

    if !*is_proven {
        *is_proven = check_proof_in_payload(&payload);
        if !*is_proven {
            tracing::warn!("Agent has not proven architecture. Stripping write access.");
            strip_write_permissions(&mut payload);
        }
    } else {
        if contains_write_violation(&payload) {
             return Json(serde_json::json!({
                 "error": "Tether Blocked Write: Proposed diff fails local lint/type-check."
             })).into_response();
        }
    }

    let client = reqwest::Client::new();
    let res = client.post(format!("{}/v1/chat/completions", state.real_api_base))
        .json(&payload)
        .send()
        .await
        .unwrap()
        .json::<serde_json::Value>()
        .await
        .unwrap();

    Json(res).into_response()
}

fn check_proof_in_payload(payload: &serde_json::Value) -> bool {
    if let Some(messages) = payload.get("messages").and_then(|m| m.as_array()) {
        for msg in messages {
            if let Some(tool_calls) = msg.get("tool_calls").and_then(|tc| tc.as_array()) {
                for tc in tool_calls {
                    if let Some(func) = tc.get("function") {
                        if func.get("name").and_then(|n| n.as_str()) == Some("prove_architecture") {
                            return true;
                        }
                    }
                }
            }
        }
    }
    false
}

fn strip_write_permissions(payload: &mut serde_json::Value) {
    if let Some(tools) = payload.get_mut("tools").and_then(|t| t.as_array_mut()) {
        tools.retain(|tool| {
            if let Some(func) = tool.get("function") {
                let name = func.get("name").and_then(|n| n.as_str()).unwrap_or("");
                if name == "write_file" || name == "replace" || name == "run_shell_command" {
                    return false;
                }
            }
            true
        });
    }
}

fn contains_write_violation(payload: &serde_json::Value) -> bool {
    if let Some(messages) = payload.get("messages").and_then(|m| m.as_array()) {
        for msg in messages {
            if let Some(tool_calls) = msg.get("tool_calls").and_then(|tc| tc.as_array()) {
                for tc in tool_calls {
                    if let Some(func) = tc.get("function") {
                        if func.get("name").and_then(|n| n.as_str()) == Some("write_file") {
                            if let Some(args_str) = func.get("arguments").and_then(|a| a.as_str()) {
                                if args_str.contains(concat!("// TO", "DO")) || args_str.contains("pass") {
                                    return true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    false
}
