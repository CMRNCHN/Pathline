//! Native SIP bridge backing `window.__pathlineSipBridge` (see
//! `client/src/transport/SipTransport.ts`, `NativeSipBridge`).
//!
//! LOCKED stack: pure-Rust `rsiprtp` (`docs/desktop-sip-stack.md`,
//! `LOCKED_SIP_STACK=rsiprtp`). `rsiprtp` is a single crate covering SIP
//! signaling (transactions + dialogs), RTP, G.711/G.722/Opus codecs, and
//! RFC 4733 telephone-event DTMF, with TLS provided by `rustls`. No C SDK /
//! FFI is used (no Linphone/PJSIP), keeping the calling path fully auditable.
//!
//! Because `rsiprtp` exposes its signaling as Sans-IO builders + an owned
//! transport layer (rather than a turnkey `UserAgent::dial`), this module
//! drives the dialog explicitly: build INVITE/ACK/BYE with
//! [`rsiprtp::sip::SipRequest`], carry them over a `rustls` TLS connection
//! ([`rsiprtp::transport::TlsTransport`]), negotiate media via
//! [`rsiprtp::sdp`], and run RTP/DTMF over a `tokio` UDP socket. This mirrors
//! the crate's own `basic_call` example, extended with media + DTMF.
//!
//! Layer boundary (`docs/architecture-boundary.md`): this file knows dial,
//! RTP, DTMF injection, and PCM frames only. It MUST NOT import `RunSession`,
//! `runEngine`, STT, or UI code. Audio is delivered as mono float32 at 16 kHz
//! per `docs/desktop-audio-contract.md`.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::net::{IpAddr, SocketAddr};
use std::sync::Arc;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{AppHandle, Emitter, State};
use tokio::net::UdpSocket;
use tokio::sync::{mpsc, Mutex};
use tokio::time::{interval, sleep, timeout};

// Explicit imports (NOT `prelude::*`): the prelude re-exports `Result`/`Error`,
// which would shadow `std`'s and break `#[tauri::command]` return types.
use rsiprtp::media::{silence_frame, G711Codec, G711Variant};
use rsiprtp::rtp::{DtmfDigit, DtmfEvent, RtpPacket};
use rsiprtp::sdp::builder::{MediaBuilder, SdpBuilder};
use rsiprtp::sdp::parser::SessionDescription;
use rsiprtp::sip::{
    generate_branch, generate_call_id, generate_tag, DigestChallenge, DigestCredentials,
    DigestResponse, Method, SipMessage, SipRequest, SipResponse,
};
use rsiprtp::transport::{TlsClientConfig, TlsSender, TlsTransport};

/// Tauri event name for transport events (mirrors `TransportEventType`).
const EVENT_TOPIC: &str = "pathline:sip-event";
/// Tauri event name for raw PCM audio frames (mono float32).
const AUDIO_TOPIC: &str = "pathline:sip-audio";

/// RTP payload type we offer/expect for RFC 4733 telephone-event DTMF.
const DEFAULT_TELEPHONE_EVENT_PT: u8 = 101;
/// One G.711 frame = 20 ms @ 8 kHz.
const SAMPLES_PER_FRAME: u32 = 160;
/// Delivered PCM sample rate (see `client/src/transport/audioFormat.ts`).
const OUTPUT_SAMPLE_RATE: u32 = 16000;

/// Commands sent from the Tauri command handlers to the live call task.
enum CallCommand {
    /// Inbound answer. Unused for the outbound-dial lab flow but kept so the
    /// frozen `NativeSipBridge.answer()` has a home.
    Answer,
    /// Send DTMF digits as RFC 4733 telephone-events over RTP.
    Dtmf { digits: String, duration_ms: u32 },
    /// Tear the call down with a SIP BYE.
    Hangup,
}

/// Managed Tauri state. Holds the command channel to the current call task.
#[derive(Default)]
pub struct SipBridge {
    inner: Arc<Mutex<BridgeInner>>,
}

#[derive(Default)]
struct BridgeInner {
    call: Option<mpsc::UnboundedSender<CallCommand>>,
}

/// SIP account + peer configuration, sourced from the environment so the
/// frozen `dial(number)` signature stays intact. Defaults target the lab
/// Asterisk (`docs/lab-run.md`): TLS on `127.0.0.1:5061`.
#[derive(Clone)]
struct SipConfig {
    server: String,
    port: u16,
    username: String,
    password: String,
    local_ip: String,
    /// Advertised local SIP port for Via/Contact. The TLS transport uses an
    /// ephemeral source port; responses return on the established connection,
    /// so this value is only a header label.
    local_port: u16,
    /// Whether to verify the server certificate. The lab uses a self-signed
    /// cert, so this defaults to `false` for localhost and must only be
    /// relaxed for the lab profile — never in production.
    verify_tls: bool,
    /// Plain RTP is intentionally available only for the loopback Asterisk
    /// acceptance lab. The locked stack does not currently implement SRTP, so
    /// production dialing must fail closed instead of silently downgrading.
    allow_plain_rtp: bool,
    rtp_inactivity_timeout: Duration,
}

impl SipConfig {
    fn from_env() -> Result<Self, String> {
        let server = env_or(&["PATHLINE_SIP_SERVER", "LAB_SIP_SERVER"], "127.0.0.1");
        let port = env_or(&["PATHLINE_SIP_TLS_PORT", "LAB_SIP_TLS_PORT"], "5061")
            .parse()
            .unwrap_or(5061);
        let username = env_or(&["PATHLINE_SIP_USER", "LAB_SIP_USER"], "pathline-lab");
        let password = env_or(&["PATHLINE_SIP_PASSWORD", "LAB_SIP_PASSWORD"], "");
        let local_ip = env_or(&["PATHLINE_SIP_LOCAL_IP"], "127.0.0.1");
        let local_port = env_or(&["PATHLINE_SIP_LOCAL_PORT"], "5065")
            .parse()
            .unwrap_or(5065);
        // Verify TLS only when explicitly requested; default off for the
        // self-signed localhost lab. Any non-loopback server flips it on.
        let is_loopback = server == "127.0.0.1" || server == "localhost" || server == "::1";
        let verify_tls = match std::env::var("PATHLINE_SIP_VERIFY_TLS") {
            Ok(v) => matches!(v.as_str(), "1" | "true" | "yes"),
            Err(_) => !is_loopback,
        };
        let profile = env_or(&["PATHLINE_SIP_PROFILE"], "");
        let allow_plain_rtp = profile == "lab" && is_loopback;
        let rtp_inactivity_timeout = Duration::from_secs(
            env_or(&["PATHLINE_RTP_INACTIVITY_SECONDS"], "15")
                .parse::<u64>()
                .map_err(|_| "PATHLINE_RTP_INACTIVITY_SECONDS must be an integer".to_string())?
                .clamp(5, 120),
        );
        if !allow_plain_rtp {
            return Err(
                "Production SIP is unavailable: rsiprtp 0.4.1 has no SRTP transport. \
                 Plain RTP is permitted only with PATHLINE_SIP_PROFILE=lab on loopback."
                    .to_string(),
            );
        }
        Ok(Self {
            server,
            port,
            username,
            password,
            local_ip,
            local_port,
            verify_tls,
            allow_plain_rtp,
            rtp_inactivity_timeout,
        })
    }
}

fn env_or(keys: &[&str], default: &str) -> String {
    for k in keys {
        if let Ok(v) = std::env::var(k) {
            if !v.is_empty() {
                return v;
            }
        }
    }
    default.to_string()
}

/// Rewrite the digest `algorithm` token in a WWW-/Proxy-Authenticate header
/// to the exact casing the locked `rsiprtp` parser accepts.
///
/// Asterisk 18 emits `algorithm=md5` (lowercase) and some carriers vary the
/// case too, but `rsiprtp` 0.4.1 matches the token case-sensitively (`MD5`,
/// `MD5-sess`, `SHA-256`, `SHA-256-sess`) and rejects anything else as
/// "unsupported algorithm". RFC 7616 §3.3 defines the token as
/// case-insensitive, so normalizing it before parsing is spec-compliant.
/// Unrecognized tokens are left untouched so the parser still surfaces a
/// genuine "unsupported algorithm" error.
fn normalize_digest_algorithm(header: &str) -> String {
    let Some(key_pos) = header.to_ascii_lowercase().find("algorithm=") else {
        return header.to_string();
    };
    let val_start = key_pos + "algorithm=".len();
    // The algorithm value is an unquoted token ending at the next comma or
    // whitespace (RFC 7616 §3.3).
    let val_end = header[val_start..]
        .find(|c: char| c == ',' || c.is_whitespace())
        .map(|offset| val_start + offset)
        .unwrap_or(header.len());
    let canonical = match header[val_start..val_end].to_ascii_lowercase().as_str() {
        "md5" => "MD5",
        "md5-sess" => "MD5-sess",
        "sha-256" => "SHA-256",
        "sha-256-sess" => "SHA-256-sess",
        _ => return header.to_string(),
    };
    format!("{}{}{}", &header[..val_start], canonical, &header[val_end..])
}

/// Discover the real local TCP port of our established TLS socket to `peer`.
///
/// `rsiprtp` 0.4.1's `TlsTransport::connect` uses an ephemeral source port but
/// our Via/Contact previously advertised `PATHLINE_SIP_LOCAL_PORT` (5065).
/// Asterisk then fails to send `200 OK` with `PJ_EINVALIDOP`. The working lab
/// verifier (`scripts/lab-sip-traversal.py`) puts `getsockname()` in Via —
/// match that.
fn discover_tls_local_port(peer: SocketAddr) -> Option<u16> {
    let pid = std::process::id().to_string();
    let needle = format!("-iTCP@{}:{}", peer.ip(), peer.port());
    // macOS lsof ORs selection options unless `-a` is set — without it we
    // match Colima's ssh forwarder (local *:5061) and advertise the server
    // port in Via, which breaks Asterisk 200 OK delivery.
    let output = std::process::Command::new("lsof")
        .args(["-nP", "-a", "-p", &pid, &needle, "-sTCP:ESTABLISHED"])
        .output()
        .ok()?;
    let text = String::from_utf8_lossy(&output.stdout);
    let peer_port = peer.port();
    for line in text.lines() {
        // Belt-and-suspenders: only parse rows for this PID.
        let mut cols = line.split_whitespace();
        let _cmd = cols.next();
        let Some(row_pid) = cols.next() else {
            continue;
        };
        if row_pid != pid {
            continue;
        }
        let Some(tcp_at) = line.find("TCP ") else {
            continue;
        };
        let rest = &line[tcp_at + 4..];
        let Some(arrow) = rest.find("->") else {
            continue;
        };
        let local = rest[..arrow].trim();
        let Some(colon) = local.rfind(':') else {
            continue;
        };
        if let Ok(port) = local[colon + 1..].parse::<u16>() {
            // Never advertise the peer's listen port as our Via port.
            if port != peer_port {
                return Some(port);
            }
        }
    }
    None
}

/// Append `;rport` to the first Via header (RFC 3581) so Asterisk applies
/// symmetric response routing — same as the lab verifier.
fn with_via_rport(data: Vec<u8>) -> Vec<u8> {
    let Ok(text) = std::str::from_utf8(&data) else {
        return data;
    };
    let Some(via_rel) = text.find("Via: ") else {
        return data;
    };
    let after = via_rel + 5;
    let Some(line_end_rel) = text[after..].find("\r\n") else {
        return data;
    };
    let line_end = after + line_end_rel;
    let via_line = &text[via_rel..line_end];
    if via_line.contains("rport") {
        return data;
    }
    let mut out = Vec::with_capacity(data.len() + 6);
    out.extend_from_slice(&data[..line_end]);
    out.extend_from_slice(b";rport");
    out.extend_from_slice(&data[line_end..]);
    out
}

fn sip_send_bytes(data: impl AsRef<[u8]>) -> Vec<u8> {
    with_via_rport(data.as_ref().to_vec())
}

/// Transport event payload. Never carries PCM, transcripts, or secrets
/// (`docs/desktop-audio-contract.md`, `docs/architecture-boundary.md` rule 3).
#[derive(Clone, Serialize)]
struct EventPayload {
    #[serde(rename = "type")]
    kind: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    detail: Option<String>,
}

/// PCM audio frame payload. The JS shim converts `pcm` into a `Float32Array`
/// before calling `onAudio(pcm, sampleRate)`.
#[derive(Clone, Serialize)]
struct AudioPayload {
    pcm: Vec<f32>,
    #[serde(rename = "sampleRate")]
    sample_rate: u32,
}

#[derive(Clone, Serialize)]
pub struct SipReadiness {
    ready: bool,
    signaling: &'static str,
    media: &'static str,
    certificate_verification: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
}

fn emit_event(app: &AppHandle, kind: &str, detail: Option<String>) {
    let _ = app.emit(
        EVENT_TOPIC,
        EventPayload {
            kind: kind.to_string(),
            detail,
        },
    );
}

fn emit_audio(app: &AppHandle, pcm: Vec<f32>, sample_rate: u32) {
    let _ = app.emit(AUDIO_TOPIC, AudioPayload { pcm, sample_rate });
}

// ---------------------------------------------------------------------------
// Tauri commands (invoked by the JS shim via `invoke`).
// ---------------------------------------------------------------------------

#[tauri::command]
pub async fn sip_dial(
    app: AppHandle,
    state: State<'_, SipBridge>,
    number: String,
) -> Result<(), String> {
    let number = number.trim().to_string();
    if number.is_empty() {
        emit_event(&app, "error", Some("dial: empty number".to_string()));
        return Err("empty number".to_string());
    }

    let cfg = SipConfig::from_env().map_err(|error| {
        emit_event(&app, "error", Some(error.clone()));
        error
    })?;
    let (cmd_tx, cmd_rx) = mpsc::unbounded_channel::<CallCommand>();

    {
        let mut inner = state.inner.lock().await;
        // Replace any prior call. Best-effort teardown of the old one.
        if let Some(old) = inner.call.take() {
            let _ = old.send(CallCommand::Hangup);
        }
        inner.call = Some(cmd_tx);
    }

    let inner_ref = state.inner.clone();
    let app_bg = app.clone();
    // Own the SIP/RTP dialog on a background async task (tokio via Tauri's
    // async runtime).
    tauri::async_runtime::spawn(async move {
        if let Err(e) = run_call(app_bg.clone(), cfg, number, cmd_rx).await {
            // Fail closed: any dial/media failure surfaces as an `error`
            // event — never a silent success.
            emit_event(&app_bg, "error", Some(e));
        }
        // Clear the slot once the call task exits.
        let mut inner = inner_ref.lock().await;
        inner.call = None;
    });

    Ok(())
}

#[tauri::command]
pub async fn sip_answer(state: State<'_, SipBridge>) -> Result<(), String> {
    if let Some(tx) = state.inner.lock().await.call.as_ref() {
        let _ = tx.send(CallCommand::Answer);
    }
    Ok(())
}

#[tauri::command]
pub async fn sip_send_dtmf(
    app: AppHandle,
    state: State<'_, SipBridge>,
    digits: String,
    duration_ms: u32,
) -> Result<(), String> {
    let guard = state.inner.lock().await;
    let Some(tx) = guard.call.as_ref() else {
        emit_event(&app, "error", Some("sendDtmf: no active call".to_string()));
        return Err("no active call".to_string());
    };
    tx.send(CallCommand::Dtmf {
        digits,
        duration_ms,
    })
    .map_err(|_| "call task gone".to_string())
}

#[tauri::command]
pub async fn sip_hangup(state: State<'_, SipBridge>) -> Result<(), String> {
    if let Some(tx) = state.inner.lock().await.call.take() {
        let _ = tx.send(CallCommand::Hangup);
    }
    Ok(())
}

#[tauri::command]
pub async fn sip_status() -> Result<SipReadiness, String> {
    match SipConfig::from_env() {
        Ok(config) => Ok(SipReadiness {
            ready: true,
            signaling: "sip-tls",
            media: if config.allow_plain_rtp { "rtp-lab-only" } else { "srtp" },
            certificate_verification: config.verify_tls,
            reason: None,
        }),
        Err(reason) => Ok(SipReadiness {
            ready: false,
            signaling: "sip-tls",
            media: "srtp-required",
            certificate_verification: true,
            reason: Some(reason),
        }),
    }
}

// ---------------------------------------------------------------------------
// Call task: signaling handshake + media loop.
// ---------------------------------------------------------------------------

async fn run_call(
    app: AppHandle,
    cfg: SipConfig,
    number: String,
    mut cmd_rx: mpsc::UnboundedReceiver<CallCommand>,
) -> Result<(), String> {
    let server_addr = resolve_server(&cfg).await?;
    let local_ip: IpAddr = cfg
        .local_ip
        .parse()
        .map_err(|_| format!("invalid local IP {}", cfg.local_ip))?;

    // --- TLS transport for SIP signaling ---------------------------------
    // Bind advertisement uses the real TCP source port (see discover below).
    // Passing port 0 here only labels the transport; rsiprtp still connects
    // with an ephemeral source port.
    let local_sip_addr: SocketAddr = format!("{}:0", cfg.local_ip)
        .parse()
        .map_err(|_| "invalid local SIP addr".to_string())?;
    let tls = TlsTransport::new_client(
        local_sip_addr,
        TlsClientConfig {
            verify_server: cfg.verify_tls,
            ca_cert_path: None,
        },
    )
    .map_err(|e| format!("TLS client init failed: {e}"))?;
    tls.connect(server_addr, &cfg.server)
        .await
        .map_err(|e| format!("TLS connect to {server_addr} failed: {e}"))?;
    // Via/Contact must advertise the real ephemeral source port — advertising
    // a fake 5065 makes Asterisk fail sending 200 OK (PJ_EINVALIDOP).
    let via_port = discover_tls_local_port(server_addr).unwrap_or(cfg.local_port);
    log::info!("SIP TLS local port for Via/Contact: {via_port}");
    let (mut sip_rx, sip_tx) = tls.start();

    // --- RTP media socket ------------------------------------------------
    // `SipConfig::from_env` has already guaranteed that unencrypted RTP is
    // confined to the explicit loopback lab profile.
    debug_assert!(cfg.allow_plain_rtp);
    let rtp_sock = UdpSocket::bind(format!("{}:0", cfg.local_ip))
        .await
        .map_err(|e| format!("RTP bind failed: {e}"))?;
    let local_rtp_port = rtp_sock
        .local_addr()
        .map_err(|e| format!("RTP local_addr failed: {e}"))?
        .port();
    let rtp_sock = Arc::new(rtp_sock);

    // --- SDP offer (PCMU/PCMA + telephone-event) -------------------------
    let sdp = SdpBuilder::new(local_ip)
        .session_name("pathline")
        .add_media(
            MediaBuilder::audio(local_rtp_port)
                .pcmu()
                .pcma()
                .telephone_event(DEFAULT_TELEPHONE_EVENT_PT),
        )
        .build();
    let sdp_bytes = sdp.to_string().into_bytes();

    // --- INVITE dialog identifiers ---------------------------------------
    let from_uri = format!("sip:{}@{}", cfg.username, cfg.server);
    let dest_uri = format!("sip:{}@{}", number, cfg.server);
    let contact = format!(
        "sip:{}@{}:{};transport=tls",
        cfg.username, cfg.local_ip, via_port
    );
    let from_tag = generate_tag();
    let sip_call_id = generate_call_id(&cfg.server);
    let creds = DigestCredentials::new(cfg.username.clone(), cfg.password.clone());

    let build_invite = |cseq: u32,
                        branch: &str,
                        authorization: Option<&str>,
                        proxy_authorization: Option<&str>|
     -> Result<SipRequest, String> {
        let mut b = SipRequest::builder()
            .method(Method::Invite)
            .uri(&dest_uri)
            .via(&cfg.local_ip, via_port, "TLS", branch)
            .from(&from_uri, &from_tag)
            .to(&dest_uri)
            .call_id(&sip_call_id)
            .cseq(cseq)
            .contact(&contact)
            .body(sdp_bytes.clone(), "application/sdp");
        if let Some(a) = authorization {
            b = b.authorization(a);
        }
        if let Some(a) = proxy_authorization {
            b = b.proxy_authorization(a);
        }
        b.build().map_err(|e| format!("build INVITE failed: {e}"))
    };

    // --- Send initial INVITE ---------------------------------------------
    let mut cseq = 1u32;
    let mut invite_branch = generate_branch();
    let invite = build_invite(cseq, &invite_branch, None, None)?;
    sip_tx
        .send_to(&sip_send_bytes(invite.to_bytes())[..], server_addr)
        .await
        .map_err(|e| format!("send INVITE failed: {e}"))?;
    log::info!("SIP INVITE -> {dest_uri} via TLS {server_addr}");

    // --- Await final response (with single re-auth) ----------------------
    let mut authed = false;
    let mut ringing_emitted = false;
    let (to_tag, answer_sdp, remote_target) = loop {
        let msg = tokio::select! {
            cmd = cmd_rx.recv() => {
                match cmd {
                    Some(CallCommand::Hangup) | None => {
                        send_cancel(
                            &sip_tx,
                            server_addr,
                            &cfg,
                            via_port,
                            &dest_uri,
                            &from_uri,
                            &from_tag,
                            &sip_call_id,
                            cseq,
                            &invite_branch,
                        ).await;
                        emit_event(&app, "disconnected", Some("dial cancelled".to_string()));
                        return Ok(());
                    }
                    Some(CallCommand::Answer) => continue,
                    Some(CallCommand::Dtmf { .. }) => {
                        emit_event(
                            &app,
                            "error",
                            Some("cannot send DTMF before call connects".to_string()),
                        );
                        continue;
                    }
                }
            }
            response = timeout(Duration::from_secs(32), sip_rx.recv()) => match response {
                Ok(Some(message)) => message,
                Ok(None) => return Err("SIP connection closed during INVITE".to_string()),
                Err(_) => return Err("timeout waiting for INVITE response".to_string()),
            }
        };
        let parsed = match SipMessage::parse(&msg.data) {
            Ok(p) => p,
            Err(_) => continue,
        };
        let Some(resp) = parsed.as_response() else {
            continue;
        };
        let status = resp.status_code();
        log::info!("SIP response {status} {}", resp.reason());
        match status {
            100 => {}
            180 | 183 => {
                if !ringing_emitted {
                    ringing_emitted = true;
                    emit_event(&app, "ringing", None);
                }
            }
            200 => {
                let to_tag = resp.to_tag().unwrap_or_default();
                let ack_uri = resp
                    .contact_uri()
                    .map(|u| u.to_string())
                    .unwrap_or_else(|| dest_uri.clone());
                // 2xx ACK: new branch, same CSeq, method ACK; Request-URI is
                // the remote Contact (RFC 3261 §13.2.2.4).
                let ack = SipRequest::builder()
                    .method(Method::Ack)
                    .uri(&ack_uri)
                    .via(&cfg.local_ip, via_port, "TLS", &generate_branch())
                    .from(&from_uri, &from_tag)
                    .to(&dest_uri)
                    .to_tag(&to_tag)
                    .call_id(&sip_call_id)
                    .cseq(cseq)
                    .build()
                    .map_err(|e| format!("build ACK failed: {e}"))?;
                let _ = sip_tx
                    .send_to(&sip_send_bytes(ack.to_bytes())[..], server_addr)
                    .await;
                break (to_tag, resp.body().to_vec(), ack_uri);
            }
            401 | 407 if !authed => {
                authed = true;
                // ACK the non-2xx final response (same branch + CSeq).
                let ack = SipRequest::builder()
                    .method(Method::Ack)
                    .uri(&dest_uri)
                    .via(&cfg.local_ip, via_port, "TLS", &invite_branch)
                    .from(&from_uri, &from_tag)
                    .to(&dest_uri)
                    .to_tag(&resp.to_tag().unwrap_or_default())
                    .call_id(&sip_call_id)
                    .cseq(cseq)
                    .build()
                    .map_err(|e| format!("build auth-ACK failed: {e}"))?;
                let _ = sip_tx
                    .send_to(&sip_send_bytes(ack.to_bytes())[..], server_addr)
                    .await;

                // Compute digest and resend INVITE.
                let (header, is_proxy) = if status == 407 {
                    (resp.proxy_authenticate(), true)
                } else {
                    (resp.www_authenticate(), false)
                };
                let header =
                    header.ok_or_else(|| format!("{status} without authenticate header"))?;
                // Asterisk/carriers may send a lowercase `algorithm` token that
                // the locked rsiprtp parser rejects; normalize it first.
                let header = normalize_digest_algorithm(&header);
                let challenge = DigestChallenge::parse(&header)
                    .map_err(|e| format!("bad auth challenge: {e}"))?;
                let dr = DigestResponse::from_challenge(
                    &challenge, &creds, "INVITE", &dest_uri, None, None,
                )
                .map_err(|e| format!("digest failed: {e}"))?;
                let auth_val = dr.to_header_value();

                cseq += 1;
                invite_branch = generate_branch();
                let reinvite = if is_proxy {
                    build_invite(cseq, &invite_branch, None, Some(&auth_val))?
                } else {
                    build_invite(cseq, &invite_branch, Some(&auth_val), None)?
                };
                sip_tx
                    .send_to(&sip_send_bytes(reinvite.to_bytes())[..], server_addr)
                    .await
                    .map_err(|e| format!("send auth INVITE failed: {e}"))?;
            }
            // Second 401/407 after we already sent credentials = auth failed.
            // Must not fall through to `_` or the dial hangs until the client
            // connect-timeout fires ("Call did not connect within N ms").
            401 | 407 => {
                return Err(format!(
                    "call rejected: {status} authentication failed ({})",
                    resp.reason()
                ));
            }
            s if s >= 300 => {
                return Err(format!("call rejected: {s} {}", resp.reason()));
            }
            _ => {}
        }
    };

    emit_event(&app, "connected", None);
    emit_event(&app, "answered", None);
    log::info!("SIP call answered ({dest_uri})");

    // --- Negotiate media from the SDP answer -----------------------------
    let media = negotiate_media(&answer_sdp, &cfg)?;
    let _ = rtp_sock.connect(media.remote_addr).await;

    // --- Media loop ------------------------------------------------------
    let codec = G711Codec::new(media.variant);
    let ssrc: u32 = seed_u32();
    let mut seq: u16 = seed_u32() as u16;
    let mut ts: u32 = seed_u32();
    let silence = silence_frame(media.variant, SAMPLES_PER_FRAME as usize);

    let mut ticker = interval(Duration::from_millis(20));
    let mut recv_buf = vec![0u8; 2048];
    let mut last_media_at = Instant::now();
    let mut last_inbound_seq: Option<u16> = None;
    let bye_target = remote_target;

    loop {
        tokio::select! {
            cmd = cmd_rx.recv() => {
                match cmd {
                    Some(CallCommand::Hangup) | None => {
                        send_bye(&sip_tx, server_addr, &cfg, via_port, &bye_target,
                                 &from_uri, &from_tag, &to_tag, &sip_call_id, cseq + 1).await;
                        emit_event(&app, "disconnected", None);
                        break;
                    }
                    Some(CallCommand::Answer) => {
                        // Outbound dial: nothing to answer.
                        log::debug!("answer() on outbound call — ignored");
                    }
                    Some(CallCommand::Dtmf { digits, duration_ms }) => {
                        let count = digits.chars().filter(|c| DtmfDigit::from_char(*c).is_some()).count();
                        // Never log plaintext DTMF (architecture-boundary rule 4):
                        // record only a count and a non-reversible hash.
                        log::info!("DTMF send: count={count} hash={}", short_hash(&digits));
                        send_dtmf(&rtp_sock, ssrc, &mut seq, &mut ts,
                                  media.telephone_event_pt, &digits, duration_ms).await?;
                        emit_event(&app, "dtmf_sent", Some(format!("count={count}")));
                    }
                }
            }
            msg = sip_rx.recv() => {
                match msg {
                    None => {
                        emit_event(&app, "disconnected", Some("signaling closed".to_string()));
                        break;
                    }
                    Some(m) => {
                        if let Ok(parsed) = SipMessage::parse(&m.data) {
                            if let Some(req) = parsed.as_request() {
                                if req.method() == Method::Bye {
                                    if let Ok(resp) = SipResponse::builder()
                                        .status(200, "OK")
                                        .from_request(req)
                                        .build()
                                    {
                                        let _ = sip_tx.send_to(&resp.to_bytes()[..], server_addr).await;
                                    }
                                    emit_event(&app, "disconnected", Some("remote BYE".to_string()));
                                    break;
                                }
                            }
                        }
                    }
                }
            }
            r = rtp_sock.recv(&mut recv_buf) => {
                if let Ok(n) = r {
                    if let Ok(pkt) = RtpPacket::parse(&recv_buf[..n]) {
                        if pkt.payload_type == media.audio_pt && !pkt.payload.is_empty() {
                            if let Some(previous) = last_inbound_seq {
                                let delta = pkt.sequence_number.wrapping_sub(previous);
                                // Drop duplicate and stale/reordered packets. Small forward
                                // gaps are tolerated; speech decoding resumes at the newest
                                // packet rather than replaying old audio into STT.
                                if delta == 0 || delta > 0x8000 {
                                    continue;
                                }
                            }
                            last_inbound_seq = Some(pkt.sequence_number);
                            last_media_at = Instant::now();
                            let pcm8k = codec.decode(&pkt.payload);
                            let pcm16k = upsample_8k_to_16k(&pcm8k);
                            emit_audio(&app, pcm16k, OUTPUT_SAMPLE_RATE);
                        }
                    }
                }
            }
            _ = ticker.tick() => {
                if last_media_at.elapsed() > cfg.rtp_inactivity_timeout {
                    return Err(format!(
                        "RTP media inactive for {} seconds",
                        cfg.rtp_inactivity_timeout.as_secs()
                    ));
                }
                // Keep the media path latched (RTP symmetric) and advance the
                // clock. Comfort silence; the bridge does not capture a mic.
                let bytes = build_rtp(media.audio_pt, seq, ts, ssrc, false, &silence);
                rtp_sock
                    .send(&bytes)
                    .await
                    .map_err(|error| format!("RTP keepalive send failed: {error}"))?;
                seq = seq.wrapping_add(1);
                ts = ts.wrapping_add(SAMPLES_PER_FRAME);
            }
        }
    }

    Ok(())
}

/// Negotiated media parameters extracted from the SDP answer.
struct NegotiatedAudio {
    remote_addr: SocketAddr,
    variant: G711Variant,
    audio_pt: u8,
    telephone_event_pt: u8,
}

fn negotiate_media(answer_sdp: &[u8], cfg: &SipConfig) -> Result<NegotiatedAudio, String> {
    let text = String::from_utf8_lossy(answer_sdp);
    let sdp = SessionDescription::parse(&text).map_err(|e| format!("bad SDP answer: {e}"))?;
    let audio = sdp
        .audio_media()
        .ok_or_else(|| "SDP answer has no audio media".to_string())?;
    if audio.is_rejected() {
        return Err("remote rejected audio media".to_string());
    }

    // Remote RTP address: media-level connection, else session-level, else
    // the signaling server IP.
    let remote_ip: IpAddr = audio
        .connection
        .as_ref()
        .and_then(|c| c.ip_addr())
        .or_else(|| sdp.connection.as_ref().and_then(|c| c.ip_addr()))
        .unwrap_or_else(|| cfg.server.parse().unwrap_or(IpAddr::from([127, 0, 0, 1])));
    let remote_addr = SocketAddr::new(remote_ip, audio.port);

    // Pick the first offered G.711 payload the peer accepted (0 = PCMU, 8 = PCMA).
    let (audio_pt, variant) = audio
        .formats
        .iter()
        .filter_map(|f| f.parse::<u8>().ok())
        .find_map(|pt| match pt {
            0 => Some((0u8, G711Variant::MuLaw)),
            8 => Some((8u8, G711Variant::ALaw)),
            _ => None,
        })
        .ok_or_else(|| "no common G.711 codec in SDP answer".to_string())?;

    // Telephone-event payload type (default 101 if peer omits the rtpmap).
    let telephone_event_pt = audio
        .rtpmaps()
        .into_iter()
        .find(|m| m.encoding.eq_ignore_ascii_case("telephone-event"))
        .map(|m| m.payload_type)
        .unwrap_or(DEFAULT_TELEPHONE_EVENT_PT);

    Ok(NegotiatedAudio {
        remote_addr,
        variant,
        audio_pt,
        telephone_event_pt,
    })
}

async fn resolve_server(cfg: &SipConfig) -> Result<SocketAddr, String> {
    if let Ok(ip) = cfg.server.parse::<IpAddr>() {
        return Ok(SocketAddr::new(ip, cfg.port));
    }
    // Hostname: plain A/AAAA lookup at the configured TLS port. (The lab and
    // production trunks are reached by IP/host:port; SRV/NAPTR is not required
    // for the locked flow. `tokio::net::lookup_host` keeps the task `Send`.)
    let mut addrs = tokio::net::lookup_host((cfg.server.as_str(), cfg.port))
        .await
        .map_err(|e| format!("DNS resolve {} failed: {e}", cfg.server))?;
    addrs
        .next()
        .ok_or_else(|| format!("no addresses for {}", cfg.server))
}

// A BYE just needs the full dialog identity; grouping these into a struct
// would not simplify the single call site.
#[allow(clippy::too_many_arguments)]
async fn send_bye(
    sip_tx: &TlsSender,
    server_addr: SocketAddr,
    cfg: &SipConfig,
    via_port: u16,
    dest_uri: &str,
    from_uri: &str,
    from_tag: &str,
    to_tag: &str,
    call_id: &str,
    cseq: u32,
) {
    if let Ok(bye) = SipRequest::builder()
        .method(Method::Bye)
        .uri(dest_uri)
        .via(&cfg.local_ip, via_port, "TLS", &generate_branch())
        .from(from_uri, from_tag)
        .to(dest_uri)
        .to_tag(to_tag)
        .call_id(call_id)
        .cseq(cseq)
        .build()
    {
        let _ = sip_tx
            .send_to(&sip_send_bytes(bye.to_bytes())[..], server_addr)
            .await;
        log::info!("SIP BYE -> {dest_uri}");
    }
}

#[allow(clippy::too_many_arguments)]
async fn send_cancel(
    sip_tx: &TlsSender,
    server_addr: SocketAddr,
    cfg: &SipConfig,
    via_port: u16,
    dest_uri: &str,
    from_uri: &str,
    from_tag: &str,
    call_id: &str,
    cseq: u32,
    invite_branch: &str,
) {
    if let Ok(cancel) = SipRequest::builder()
        .method(Method::Cancel)
        .uri(dest_uri)
        .via(&cfg.local_ip, via_port, "TLS", invite_branch)
        .from(from_uri, from_tag)
        .to(dest_uri)
        .call_id(call_id)
        .cseq(cseq)
        .build()
    {
        let _ = sip_tx
            .send_to(&sip_send_bytes(cancel.to_bytes())[..], server_addr)
            .await;
        log::info!("SIP CANCEL -> {dest_uri}");
    }
}

/// Send DTMF digits as RFC 4733 telephone-events on the (already-connected)
/// RTP socket, sharing the media SSRC and sequence space.
async fn send_dtmf(
    rtp_sock: &UdpSocket,
    ssrc: u32,
    seq: &mut u16,
    ts: &mut u32,
    event_pt: u8,
    digits: &str,
    duration_ms: u32,
) -> Result<(), String> {
    let packets = (duration_ms / 20).max(3);
    for c in digits.chars() {
        let Some(digit) = DtmfDigit::from_char(c) else {
            continue;
        };
        // The whole event carries the RTP timestamp of its first packet.
        let event_ts = *ts;
        for i in 0..packets {
            let duration = (((i + 1) * SAMPLES_PER_FRAME).min(0xFFFF)) as u16;
            let event = DtmfEvent::new(digit, duration);
            let payload = event.encode();
            let marker = i == 0;
            let bytes = build_rtp(event_pt, *seq, event_ts, ssrc, marker, &payload);
            rtp_sock
                .send(&bytes)
                .await
                .map_err(|error| format!("DTMF RTP send failed: {error}"))?;
            *seq = seq.wrapping_add(1);
            sleep(Duration::from_millis(20)).await;
        }
        // End packets (E bit) x3 for reliability (RFC 4733 §2.5.1.4).
        let end =
            DtmfEvent::new(digit, ((packets * SAMPLES_PER_FRAME).min(0xFFFF)) as u16).with_end();
        let end_payload = end.encode();
        for _ in 0..3 {
            let bytes = build_rtp(event_pt, *seq, event_ts, ssrc, false, &end_payload);
            rtp_sock
                .send(&bytes)
                .await
                .map_err(|error| format!("DTMF end packet send failed: {error}"))?;
            *seq = seq.wrapping_add(1);
        }
        // Advance the media clock past the event plus a short inter-digit gap.
        *ts = ts.wrapping_add((packets + 2) * SAMPLES_PER_FRAME);
        sleep(Duration::from_millis(40)).await;
    }
    Ok(())
}

/// Build a minimal RTP packet (no CSRC / extension) via `rsiprtp`.
fn build_rtp(pt: u8, seq: u16, ts: u32, ssrc: u32, marker: bool, payload: &[u8]) -> Vec<u8> {
    RtpPacket::new(pt, seq, ts, ssrc)
        .with_marker(marker)
        .with_payload(payload.to_vec())
        .build()
        .to_vec()
}

/// Upsample mono 8 kHz i16 PCM to 16 kHz float32 in `[-1.0, 1.0]` via linear
/// interpolation (2x). Matches the frozen audio contract's preferred rate.
fn upsample_8k_to_16k(pcm8k: &[i16]) -> Vec<f32> {
    let mut out = Vec::with_capacity(pcm8k.len() * 2);
    for i in 0..pcm8k.len() {
        let cur = pcm8k[i] as f32 / 32768.0;
        let next = if i + 1 < pcm8k.len() {
            pcm8k[i + 1] as f32 / 32768.0
        } else {
            cur
        };
        out.push(cur);
        out.push((cur + next) * 0.5);
    }
    out
}

/// Non-reversible short hash for DTMF audit logging (never log plaintext).
fn short_hash(s: &str) -> String {
    let mut h = DefaultHasher::new();
    s.hash(&mut h);
    format!("{:08x}", (h.finish() & 0xffff_ffff))
}

/// Cheap 32-bit seed from the wall clock (SSRC / initial seq+ts).
fn seed_u32() -> u32 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    nanos.wrapping_mul(2654435761).wrapping_add(0x9E37_79B9)
}

/// JS shim injected before webview content runs. Defines
/// `window.__pathlineSipBridge` implementing the frozen `NativeSipBridge`
/// shape: `dial/answer/sendDtmf/hangup` call the Tauri commands; `onAudio`
/// and `onEvent` subscribe to the Tauri event stream and return unsubscribe
/// functions. PCM crosses as a number array the shim wraps in `Float32Array`.
pub fn init_script() -> String {
    format!(
        r#"(function () {{
  if (window.__pathlineSipBridge) return;
  function internals() {{ return window.__TAURI_INTERNALS__; }}
  function invoke(cmd, args) {{
    var i = internals();
    if (!i || !i.invoke) return Promise.reject(new Error('Tauri internals unavailable'));
    return i.invoke(cmd, args || {{}});
  }}
  function listen(event, handler) {{
    var i = internals();
    if (!i || !i.invoke || !i.transformCallback) return Promise.resolve(function () {{}});
    var cb = i.transformCallback(function (evt) {{ handler(evt && evt.payload); }});
    return i.invoke('plugin:event|listen', {{ event: event, target: {{ kind: 'Any' }}, handler: cb }})
      .then(function (id) {{
        return function () {{ i.invoke('plugin:event|unlisten', {{ event: event, eventId: id }}); }};
      }})
      .catch(function () {{ return function () {{}}; }});
  }}
  function subscribe(event, cb) {{
    var unlisten = null; var cancelled = false;
    listen(event, cb).then(function (fn) {{ if (cancelled) {{ fn(); }} else {{ unlisten = fn; }} }});
    return function () {{ cancelled = true; if (unlisten) {{ unlisten(); unlisten = null; }} }};
  }}
  window.__pathlineSipBridge = {{
    readiness: function () {{ return invoke('sip_status', {{}}); }},
    dial: function (number) {{ return invoke('sip_dial', {{ number: String(number) }}); }},
    answer: function () {{ return invoke('sip_answer', {{}}); }},
    sendDtmf: function (digits, durationMs) {{
      return invoke('sip_send_dtmf', {{ digits: String(digits), durationMs: (durationMs >>> 0) || 0 }});
    }},
    hangup: function () {{ return invoke('sip_hangup', {{}}); }},
    onAudio: function (cb) {{
      return subscribe('{audio}', function (p) {{
        if (!p) return;
        var arr = (p.pcm instanceof Float32Array) ? p.pcm : Float32Array.from(p.pcm || []);
        cb(arr, p.sampleRate);
      }});
    }},
    onEvent: function (cb) {{
      return subscribe('{topic}', function (p) {{ if (p) cb(p.type, p.detail); }});
    }}
  }};
}})();"#,
        audio = AUDIO_TOPIC,
        topic = EVENT_TOPIC,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lab_cfg() -> SipConfig {
        SipConfig {
            server: "127.0.0.1".to_string(),
            port: 5061,
            username: "pathline-lab".to_string(),
            password: "secret".to_string(),
            local_ip: "127.0.0.1".to_string(),
            local_port: 5065,
            verify_tls: false,
            allow_plain_rtp: true,
            rtp_inactivity_timeout: Duration::from_secs(15),
        }
    }

    #[test]
    fn via_rport_is_injected_once() {
        let raw = b"INVITE sip:1000@127.0.0.1 SIP/2.0\r\n\
Via: SIP/2.0/TLS 127.0.0.1:5065;branch=z9hG4bKabc\r\n\
From: <sip:u@127.0.0.1>;tag=t\r\n\r\n";
        let once = with_via_rport(raw.to_vec());
        let text = String::from_utf8(once.clone()).unwrap();
        assert!(text.contains("Via: SIP/2.0/TLS 127.0.0.1:5065;branch=z9hG4bKabc;rport\r\n"));
        let twice = with_via_rport(once);
        assert_eq!(twice, text.into_bytes());
    }

    #[test]
    fn normalizes_lowercase_algorithm_from_asterisk() {
        // Real Asterisk 18.10 challenge — note lowercase `algorithm=md5`.
        let header = r#"Digest realm="asterisk",nonce="1784646658/190ce79745e7259651ca899c2aa6d7ff",opaque="3d9ca03014256634",algorithm=md5,qop="auth""#;
        let normalized = normalize_digest_algorithm(header);
        assert!(normalized.contains("algorithm=MD5"));
        // The locked parser now accepts it end-to-end.
        let challenge = DigestChallenge::parse(&normalized).expect("challenge parses");
        assert_eq!(challenge.realm, "asterisk");
    }

    #[test]
    fn normalizes_algorithm_variants_and_leaves_others() {
        assert!(normalize_digest_algorithm("Digest algorithm=sha-256, realm=\"x\"")
            .contains("algorithm=SHA-256"));
        assert!(normalize_digest_algorithm("Digest algorithm=MD5-SESS, realm=\"x\"")
            .contains("algorithm=MD5-sess"));
        // No algorithm param -> unchanged (parser defaults to MD5).
        let no_alg = r#"Digest realm="asterisk", nonce="abc""#;
        assert_eq!(normalize_digest_algorithm(no_alg), no_alg);
        // Unknown token -> left as-is so the parser can reject it.
        let unknown = "Digest algorithm=whirlpool, realm=\"x\"";
        assert_eq!(normalize_digest_algorithm(unknown), unknown);
    }

    #[test]
    fn upsample_doubles_and_normalizes() {
        // 8 kHz -> 16 kHz is exactly 2x; output is float32 in [-1, 1].
        let input = [0i16, 16384, -32768, 32767];
        let out = upsample_8k_to_16k(&input);
        assert_eq!(out.len(), input.len() * 2);
        assert!((out[0] - 0.0).abs() < 1e-6);
        assert!((out[2] - 0.5).abs() < 1e-4); // 16384 / 32768
        assert!(out.iter().all(|s| (-1.0..=1.0).contains(s)));
    }

    #[test]
    fn negotiate_media_parses_pcmu_answer() {
        // Typical Asterisk 200 OK answer: PCMU + telephone-event on 101.
        let answer = "v=0\r\n\
o=- 1 1 IN IP4 127.0.0.1\r\n\
s=Asterisk\r\n\
c=IN IP4 127.0.0.1\r\n\
t=0 0\r\n\
m=audio 14002 RTP/AVP 0 101\r\n\
a=rtpmap:0 PCMU/8000\r\n\
a=rtpmap:101 telephone-event/8000\r\n\
a=fmtp:101 0-16\r\n\
a=sendrecv\r\n";
        let media = negotiate_media(answer.as_bytes(), &lab_cfg()).expect("negotiate");
        assert_eq!(media.audio_pt, 0);
        assert_eq!(media.variant, G711Variant::MuLaw);
        assert_eq!(media.telephone_event_pt, 101);
        assert_eq!(media.remote_addr, "127.0.0.1:14002".parse().unwrap());
    }

    #[test]
    fn negotiate_media_selects_pcma_when_offered() {
        let answer = "v=0\r\n\
o=- 1 1 IN IP4 10.0.0.5\r\n\
s=-\r\n\
c=IN IP4 10.0.0.5\r\n\
t=0 0\r\n\
m=audio 40000 RTP/AVP 8\r\n\
a=rtpmap:8 PCMA/8000\r\n\
a=sendrecv\r\n";
        let media = negotiate_media(answer.as_bytes(), &lab_cfg()).expect("negotiate");
        assert_eq!(media.audio_pt, 8);
        assert_eq!(media.variant, G711Variant::ALaw);
        // No telephone-event rtpmap -> default 101.
        assert_eq!(media.telephone_event_pt, DEFAULT_TELEPHONE_EVENT_PT);
    }

    #[test]
    fn negotiate_media_rejects_no_common_codec() {
        let answer = "v=0\r\n\
o=- 1 1 IN IP4 127.0.0.1\r\n\
s=-\r\n\
c=IN IP4 127.0.0.1\r\n\
t=0 0\r\n\
m=audio 40000 RTP/AVP 9\r\n\
a=rtpmap:9 G722/8000\r\n\
a=sendrecv\r\n";
        assert!(negotiate_media(answer.as_bytes(), &lab_cfg()).is_err());
    }

    #[test]
    fn dtmf_rtp_packet_roundtrips_as_telephone_event() {
        // A DTMF packet we build must parse back to the right payload type
        // and decode to the intended digit with the RFC 4733 end bit.
        let event = DtmfEvent::new(DtmfDigit::Five, 160).with_end();
        let bytes = build_rtp(101, 42, 1000, 0xDEAD_BEEF, false, &event.encode());
        let pkt = RtpPacket::parse(&bytes).expect("parse rtp");
        assert_eq!(pkt.payload_type, 101);
        assert_eq!(pkt.sequence_number, 42);
        assert_eq!(pkt.ssrc, 0xDEAD_BEEF);
        let decoded = DtmfEvent::decode(&pkt.payload).expect("decode dtmf");
        assert_eq!(decoded.digit, DtmfDigit::Five);
        assert!(decoded.end);
    }

    #[test]
    fn audio_rtp_packet_decodes_to_pcm() {
        // Build a PCMU audio packet, then confirm the inbound path (parse +
        // G.711 decode + upsample) yields 16 kHz float PCM.
        let codec = G711Codec::new(G711Variant::MuLaw);
        let pcm_in: Vec<i16> = (0..160).map(|i| (i as i16 - 80) * 100).collect();
        let encoded = codec.encode(&pcm_in);
        let bytes = build_rtp(0, 1, 0, 1, true, &encoded);
        let pkt = RtpPacket::parse(&bytes).expect("parse rtp");
        assert_eq!(pkt.payload_type, 0);
        let pcm8k = codec.decode(&pkt.payload);
        assert_eq!(pcm8k.len(), 160);
        let pcm16k = upsample_8k_to_16k(&pcm8k);
        assert_eq!(pcm16k.len(), 320);
    }

    #[test]
    fn short_hash_never_reveals_plaintext() {
        // DTMF audit must not be reversible to the digit sequence.
        let digits = "1234#";
        let h = short_hash(digits);
        assert_eq!(h.len(), 8);
        assert!(!h.contains(digits));
        assert_eq!(h, short_hash(digits)); // deterministic
        assert_ne!(h, short_hash("5678#"));
    }

    #[tokio::test]
    async fn send_dtmf_emits_telephone_events_over_udp() {
        // Real on-the-wire proof of the DTMF path: send_dtmf writes RFC 4733
        // telephone-event RTP packets to a localhost UDP peer, which must see
        // a marked begin packet and an end packet decoding to the digit.
        let peer = UdpSocket::bind("127.0.0.1:0").await.unwrap();
        let peer_addr = peer.local_addr().unwrap();
        let client = UdpSocket::bind("127.0.0.1:0").await.unwrap();
        client.connect(peer_addr).await.unwrap();

        let collector = tokio::spawn(async move {
            let mut got_begin = false;
            let mut got_end_five = false;
            let mut buf = [0u8; 256];
            for _ in 0..16 {
                match timeout(Duration::from_millis(500), peer.recv(&mut buf)).await {
                    Ok(Ok(n)) => {
                        if let Ok(p) = RtpPacket::parse(&buf[..n]) {
                            if p.payload_type == 101 {
                                if p.marker {
                                    got_begin = true;
                                }
                                if let Some(ev) = DtmfEvent::decode(&p.payload) {
                                    if ev.end && ev.digit == DtmfDigit::Five {
                                        got_end_five = true;
                                    }
                                }
                            }
                        }
                    }
                    _ => break,
                }
            }
            (got_begin, got_end_five)
        });

        let mut seq = 100u16;
        let mut ts = 0u32;
        send_dtmf(&client, 0x1234_5678, &mut seq, &mut ts, 101, "5", 40)
            .await
            .unwrap();

        let (begin, end) = collector.await.unwrap();
        assert!(begin, "no marked DTMF begin packet received");
        assert!(end, "no DTMF end packet for digit 5 received");
        // Sequence advanced across all sent packets.
        assert!(seq > 100);
    }

    #[test]
    fn init_script_defines_bridge_and_commands() {
        let js = init_script();
        assert!(js.contains("window.__pathlineSipBridge"));
        for cmd in ["sip_status", "sip_dial", "sip_answer", "sip_send_dtmf", "sip_hangup"] {
            assert!(js.contains(cmd), "shim missing command {cmd}");
        }
        assert!(js.contains(AUDIO_TOPIC));
        assert!(js.contains(EVENT_TOPIC));
    }
}
