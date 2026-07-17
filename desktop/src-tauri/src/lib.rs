mod sip_bridge;

use sip_bridge::SipBridge;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    // Inject `window.__pathlineSipBridge` before webview content runs.
    .plugin(
      tauri::plugin::Builder::<tauri::Wry>::new("pathline-sip")
        .js_init_script(sip_bridge::init_script())
        .build(),
    )
    .manage(SipBridge::default())
    .invoke_handler(tauri::generate_handler![
      sip_bridge::sip_dial,
      sip_bridge::sip_answer,
      sip_bridge::sip_send_dtmf,
      sip_bridge::sip_hangup,
    ])
    .setup(|app| {
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
