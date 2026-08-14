//! Defines the API origin for the embedded webview.
//!
//! Release builds inject `PATHLINE_API_URL` at compile time. Development uses
//! the managed localhost API started by `scripts/desktop-dev.sh`.

pub fn init_script() -> String {
    // Prefer an explicit release origin. When unset, default to the local
    // uvicorn sidecar — a blank value made the webview fall through to Vite's
    // `/api` proxy path, which returns HTML and surfaces WebKit's cryptic
    // "The string did not match the expected pattern" on consent/token mint.
    let configured = option_env!("PATHLINE_API_URL");
    let value = configured.unwrap_or("http://127.0.0.1:8000");
    format!(
        "window.__pathlineApiBase = {};",
        serde_json::to_string(value).expect("serialize API URL")
    )
}

#[cfg(test)]
mod tests {
    #[test]
    fn api_boundary_is_absolute_http_origin() {
        let script = super::init_script();
        assert!(script.contains("window.__pathlineApiBase"));
        assert!(
            script.contains("http://127.0.0.1:8000") || script.contains("https://"),
            "desktop must inject an absolute API origin, not the Vite /api proxy"
        );
        assert!(!script.contains("\"/api\""));
    }
}
