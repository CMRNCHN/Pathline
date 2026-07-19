//! Local-only whisper.cpp bridge backing `window.__pathlineWhisper`.
//!
//! Audio enters as mono 16 kHz float32 PCM and transcript text returns directly
//! to the webview. This module has no network client and never persists audio or
//! transcript data.

use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::Serialize;
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager, State};
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

const MODEL_FILENAME: &str = "ggml-tiny.en.bin";
const MODEL_SHA256: &str = "921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f";
const REQUIRED_SAMPLE_RATE: u32 = 16_000;
const MAX_AUDIO_SECONDS: usize = 30;

#[derive(Clone)]
pub struct WhisperBridge {
    inner: Arc<WhisperInner>,
}

struct WhisperInner {
    model_path: PathBuf,
    context: Mutex<Option<Arc<WhisperContext>>>,
}

#[derive(Clone, Serialize)]
pub struct WhisperReadiness {
    ready: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
    model: String,
    license: String,
    sha256: String,
}

impl WhisperBridge {
    pub fn new(app: &AppHandle) -> Self {
        Self {
            inner: Arc::new(WhisperInner {
                model_path: resolve_model_path(app),
                context: Mutex::new(None),
            }),
        }
    }

    fn ensure_context(&self) -> Result<Arc<WhisperContext>, String> {
        let mut guard = self
            .inner
            .context
            .lock()
            .map_err(|_| "Whisper runtime lock poisoned".to_string())?;
        if let Some(context) = guard.as_ref() {
            return Ok(context.clone());
        }

        // The default whisper.cpp logger can include decoded tokens in debug
        // builds. Install no-backend hooks so transcripts never reach logs.
        whisper_rs::install_logging_hooks();
        verify_model(&self.inner.model_path)?;
        let model_path = self.inner.model_path.to_string_lossy();
        let context = WhisperContext::new_with_params(
            model_path.as_ref(),
            WhisperContextParameters::default(),
        )
        .map_err(|error| format!("Whisper model initialization failed: {error}"))?;
        let context = Arc::new(context);
        *guard = Some(context.clone());
        Ok(context)
    }

    fn readiness(&self) -> WhisperReadiness {
        let (ready, reason) = match self.ensure_context() {
            Ok(_) => (true, None),
            Err(reason) => (false, Some(reason)),
        };
        WhisperReadiness {
            ready,
            reason,
            model: MODEL_FILENAME.to_string(),
            license: "MIT".to_string(),
            sha256: MODEL_SHA256.to_string(),
        }
    }
}

fn resolve_model_path(app: &AppHandle) -> PathBuf {
    if let Some(path) = std::env::var_os("PATHLINE_WHISPER_MODEL") {
        return PathBuf::from(path);
    }

    let bundled = app
        .path()
        .resource_dir()
        .ok()
        .map(|dir| dir.join("models").join(MODEL_FILENAME));
    if let Some(path) = bundled.filter(|path| path.is_file()) {
        return path;
    }

    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("resources")
        .join("models")
        .join(MODEL_FILENAME)
}

fn verify_model(path: &Path) -> Result<(), String> {
    let mut file = File::open(path).map_err(|_| {
        format!(
            "Bundled Whisper model is missing at {}. Run desktop/src-tauri/resources/models/fetch-model.sh.",
            path.display()
        )
    })?;
    let mut hasher = Sha256::new();
    let mut chunk = [0_u8; 1024 * 1024];
    loop {
        let read = file
            .read(&mut chunk)
            .map_err(|error| format!("Whisper model read failed: {error}"))?;
        if read == 0 {
            break;
        }
        hasher.update(&chunk[..read]);
    }
    let actual = format!("{:x}", hasher.finalize());
    if actual != MODEL_SHA256 {
        return Err(format!(
            "Whisper model checksum mismatch (expected {MODEL_SHA256}, got {actual})"
        ));
    }
    Ok(())
}

#[tauri::command]
pub async fn whisper_status(state: State<'_, WhisperBridge>) -> Result<WhisperReadiness, String> {
    let bridge = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || bridge.readiness())
        .await
        .map_err(|error| format!("Whisper readiness task failed: {error}"))
}

#[tauri::command]
pub async fn whisper_transcribe(
    state: State<'_, WhisperBridge>,
    pcm: Vec<f32>,
    sample_rate: u32,
) -> Result<String, String> {
    if sample_rate != REQUIRED_SAMPLE_RATE {
        return Err(format!(
            "Whisper requires {REQUIRED_SAMPLE_RATE} Hz mono PCM; received {sample_rate} Hz"
        ));
    }
    if pcm.is_empty() {
        return Ok(String::new());
    }
    if pcm.len() > REQUIRED_SAMPLE_RATE as usize * MAX_AUDIO_SECONDS {
        return Err(format!(
            "Whisper utterance exceeds the {MAX_AUDIO_SECONDS}-second local limit"
        ));
    }
    if pcm.iter().any(|sample| !sample.is_finite()) {
        return Err("Whisper PCM contains a non-finite sample".to_string());
    }

    let bridge = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || transcribe(&bridge, &pcm))
        .await
        .map_err(|error| format!("Whisper transcription task failed: {error}"))?
}

fn transcribe(bridge: &WhisperBridge, pcm: &[f32]) -> Result<String, String> {
    let context = bridge.ensure_context()?;
    let mut state = context
        .create_state()
        .map_err(|error| format!("Whisper state creation failed: {error}"))?;
    let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
    params.set_language(Some("en"));
    params.set_translate(false);
    params.set_print_progress(false);
    params.set_print_realtime(false);
    params.set_print_special(false);
    params.set_print_timestamps(false);
    params.set_no_context(true);

    state
        .full(params, pcm)
        .map_err(|error| format!("Local Whisper inference failed: {error}"))?;
    let segment_count = state.full_n_segments();
    let mut transcript = String::new();
    for index in 0..segment_count {
        let segment = state
            .get_segment(index)
            .ok_or_else(|| format!("Whisper segment {index} is unavailable"))?;
        transcript.push_str(
            &segment
                .to_str_lossy()
                .map_err(|error| format!("Whisper segment read failed: {error}"))?,
        );
    }
    Ok(transcript.trim().to_string())
}

pub fn init_script() -> &'static str {
    r#"(function () {
  if (window.__pathlineWhisper) return;
  function invoke(cmd, args) {
    var i = window.__TAURI_INTERNALS__;
    if (!i || !i.invoke) return Promise.reject(new Error('Tauri internals unavailable'));
    return i.invoke(cmd, args || {});
  }
  window.__pathlineWhisper = {
    readiness: function () { return invoke('whisper_status', {}); },
    transcribe: function (pcm, sampleRate) {
      var samples = Array.from(pcm || []);
      return invoke('whisper_transcribe', {
        pcm: samples,
        sampleRate: sampleRate >>> 0
      });
    }
  };
})();"#
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn model_contract_is_pinned() {
        assert_eq!(MODEL_FILENAME, "ggml-tiny.en.bin");
        assert_eq!(MODEL_SHA256.len(), 64);
        assert!(MODEL_SHA256.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn init_script_is_local_tauri_bridge() {
        let script = init_script();
        assert!(script.contains("window.__pathlineWhisper"));
        assert!(script.contains("whisper_status"));
        assert!(script.contains("whisper_transcribe"));
        assert!(!script.contains("fetch("));
    }

    #[test]
    fn bundled_model_loads_and_runs_local_inference() {
        let model_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("resources")
            .join("models")
            .join(MODEL_FILENAME);
        verify_model(&model_path).expect("bundled model checksum");
        let bridge = WhisperBridge {
            inner: Arc::new(WhisperInner {
                model_path,
                context: Mutex::new(None),
            }),
        };
        let silence = vec![0.0_f32; REQUIRED_SAMPLE_RATE as usize];
        let transcript = transcribe(&bridge, &silence).expect("local inference");
        assert!(
            transcript.len() < 128,
            "silence produced an implausible transcript"
        );
    }

    #[test]
    fn missing_or_corrupt_model_fails_closed() {
        let missing = std::env::temp_dir().join("pathline-missing-whisper-model.bin");
        let _ = std::fs::remove_file(&missing);
        assert!(verify_model(&missing).unwrap_err().contains("missing"));

        let corrupt = std::env::temp_dir().join(format!(
            "pathline-corrupt-whisper-model-{}.bin",
            std::process::id()
        ));
        std::fs::write(&corrupt, b"not a whisper model").expect("write corrupt fixture");
        let error = verify_model(&corrupt).unwrap_err();
        let _ = std::fs::remove_file(corrupt);
        assert!(error.contains("checksum mismatch"));
    }
}
