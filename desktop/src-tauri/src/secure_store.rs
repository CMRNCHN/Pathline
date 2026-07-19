//! Encrypted on-device Run History storage.
//!
//! The AES-256 key is held by macOS Keychain and never written to the app data
//! directory. The data file contains only an AES-GCM nonce and ciphertext.

use std::fs;
use std::path::PathBuf;

use aes_gcm::aead::{Aead, KeyInit};
use aes_gcm::{Aes256Gcm, Nonce};
use base64::engine::general_purpose::STANDARD;
use base64::Engine;
use rand::RngCore;
use tauri::{AppHandle, Manager};

const SERVICE: &str = "com.pathline.desktop";
const ACCOUNT: &str = "run-history-encryption-key-v1";
const FILE_NAME: &str = "run-history.v1.enc";
const NONCE_LEN: usize = 12;

fn data_path(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Cannot resolve Pathline data directory: {error}"))?;
    fs::create_dir_all(&dir).map_err(|error| format!("Cannot create Pathline data directory: {error}"))?;
    Ok(dir.join(FILE_NAME))
}

#[cfg(target_os = "macos")]
fn key_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new(SERVICE, ACCOUNT).map_err(|error| format!("Keychain unavailable: {error}"))
}

#[cfg(target_os = "macos")]
fn load_or_create_key() -> Result<[u8; 32], String> {
    let entry = key_entry()?;
    if let Ok(encoded) = entry.get_password() {
        let bytes = STANDARD
            .decode(encoded)
            .map_err(|_| "Keychain contains an invalid Pathline key".to_string())?;
        return bytes
            .try_into()
            .map_err(|_| "Keychain contains a Pathline key of the wrong length".to_string());
    }

    let mut key = [0_u8; 32];
    rand::rng().fill_bytes(&mut key);
    entry
        .set_password(&STANDARD.encode(key))
        .map_err(|error| format!("Cannot save Pathline key in Keychain: {error}"))?;
    Ok(key)
}

#[cfg(not(target_os = "macos"))]
fn load_or_create_key() -> Result<[u8; 32], String> {
    Err("OS-protected local storage is currently available only on macOS".to_string())
}

#[tauri::command]
pub async fn secure_history_load(app: AppHandle) -> Result<String, String> {
    let path = data_path(&app)?;
    if !path.exists() {
        return Ok("[]".to_string());
    }
    let payload = fs::read(path).map_err(|error| format!("Cannot read encrypted Run History: {error}"))?;
    if payload.len() <= NONCE_LEN {
        return Err("Encrypted Run History is truncated".to_string());
    }
    let key = load_or_create_key()?;
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|_| "Invalid local storage key".to_string())?;
    let plaintext = cipher
        .decrypt(Nonce::from_slice(&payload[..NONCE_LEN]), &payload[NONCE_LEN..])
        .map_err(|_| "Run History authentication failed; data was modified or the Keychain key changed".to_string())?;
    String::from_utf8(plaintext).map_err(|_| "Decrypted Run History is not valid UTF-8".to_string())
}

#[tauri::command]
pub async fn secure_history_save(app: AppHandle, json: String) -> Result<(), String> {
    serde_json::from_str::<serde_json::Value>(&json)
        .map_err(|_| "Run History payload is not valid JSON".to_string())?;
    let key = load_or_create_key()?;
    let cipher = Aes256Gcm::new_from_slice(&key).map_err(|_| "Invalid local storage key".to_string())?;
    let mut nonce = [0_u8; NONCE_LEN];
    rand::rng().fill_bytes(&mut nonce);
    let ciphertext = cipher
        .encrypt(Nonce::from_slice(&nonce), json.as_bytes())
        .map_err(|_| "Run History encryption failed".to_string())?;
    let path = data_path(&app)?;
    let temporary = path.with_extension("tmp");
    let mut payload = nonce.to_vec();
    payload.extend_from_slice(&ciphertext);
    fs::write(&temporary, payload).map_err(|error| format!("Cannot write encrypted Run History: {error}"))?;
    fs::rename(temporary, path).map_err(|error| format!("Cannot atomically save Run History: {error}"))
}

#[tauri::command]
pub async fn secure_history_clear(app: AppHandle) -> Result<(), String> {
    let path = data_path(&app)?;
    if path.exists() {
        fs::remove_file(path).map_err(|error| format!("Cannot delete encrypted Run History: {error}"))?;
    }
    #[cfg(target_os = "macos")]
    {
        let entry = key_entry()?;
        match entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => {}
            Err(error) => return Err(format!("Cannot delete Pathline Keychain key: {error}")),
        }
    }
    Ok(())
}

pub fn init_script() -> &'static str {
    r#"(function () {
  if (window.__pathlineSecureHistory) return;
  function invoke(cmd, args) {
    var i = window.__TAURI_INTERNALS__;
    if (!i || !i.invoke) return Promise.reject(new Error('Tauri internals unavailable'));
    return i.invoke(cmd, args || {});
  }
  window.__pathlineSecureHistory = {
    load: function () { return invoke('secure_history_load', {}); },
    save: function (json) { return invoke('secure_history_save', { json: String(json) }); },
    clear: function () { return invoke('secure_history_clear', {}); }
  };
})();"#
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn storage_contract_uses_authenticated_encryption() {
        assert_eq!(NONCE_LEN, 12);
        assert_eq!(FILE_NAME, "run-history.v1.enc");
        assert!(init_script().contains("secure_history_save"));
        assert!(!init_script().contains("localStorage"));
    }
}
