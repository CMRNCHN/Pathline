mod api_boundary;
mod sip_bridge;
mod secure_store;
mod whisper_bridge;

use sip_bridge::SipBridge;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri::plugin::Builder::<tauri::Wry>::new("pathline-api-boundary")
                .js_init_script(api_boundary::init_script())
                .build(),
        )
        // Inject `window.__pathlineSipBridge` before webview content runs.
        .plugin(
            tauri::plugin::Builder::<tauri::Wry>::new("pathline-sip")
                .js_init_script(sip_bridge::init_script())
                .build(),
        )
        // Inject the local-only whisper.cpp bridge before webview content runs.
        .plugin(
            tauri::plugin::Builder::<tauri::Wry>::new("pathline-whisper")
                .js_init_script(whisper_bridge::init_script())
                .build(),
        )
        .plugin(
            tauri::plugin::Builder::<tauri::Wry>::new("pathline-secure-history")
                .js_init_script(secure_store::init_script())
                .build(),
        )
        .manage(SipBridge::default())
        .invoke_handler(tauri::generate_handler![
            sip_bridge::sip_status,
            sip_bridge::sip_dial,
            sip_bridge::sip_answer,
            sip_bridge::sip_send_dtmf,
            sip_bridge::sip_hangup,
            whisper_bridge::whisper_status,
            whisper_bridge::whisper_transcribe,
            secure_store::secure_history_load,
            secure_store::secure_history_save,
            secure_store::secure_history_clear,
        ])
        .setup(|app| {
            app.manage(whisper_bridge::WhisperBridge::new(&app.handle()));
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
