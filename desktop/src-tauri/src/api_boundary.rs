//! Defines the API origin for the embedded webview.
//!
//! Release builds inject `PATHLINE_API_URL` at compile time. Development uses
//! the managed localhost API started by `scripts/desktop-dev.sh`.

pub fn init_script() -> String {
    let configured = option_env!("PATHLINE_API_URL");
    let value = configured.unwrap_or(if cfg!(debug_assertions) {
        "http://127.0.0.1:8000"
    } else {
        ""
    });
    format!(
        "window.__pathlineApiBase = {};",
        serde_json::to_string(value).expect("serialize API URL")
    )
}

#[cfg(test)]
mod tests {
    #[test]
    fn release_api_boundary_is_absolute_or_empty() {
        let script = super::init_script();
        assert!(script.contains("window.__pathlineApiBase"));
        assert!(!script.contains("\"/api\""));
    }
}
