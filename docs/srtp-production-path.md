# SRTP production path (Pathline desktop)

**Status:** Research + lab scaffolding spike (2026-07-30)  
**Locked stack:** `rsiprtp 0.4.1` (`docs/desktop-sip-stack.md`)  
**Current behavior:** Dial fails closed unless `PATHLINE_SIP_PROFILE=lab` on
loopback (`desktop/src-tauri/src/sip_bridge.rs` → `SipConfig::from_env`).
The bridge still offers RTP/AVP only; production is not open.

## What “ready for live calls” means

| Environment | Media | Gate |
|-------------|-------|------|
| Lab Asterisk (loopback) | Plain RTP | Allowed today with `PATHLINE_SIP_PROFILE=lab` |
| Lab Asterisk SRTP spike | SDES-SRTP required by Asterisk | Config scaffolding only; Pathline bridge cannot complete this call yet |
| Production SIP trunk | **SRTP (SDES)** | Required before fail-open; not wired in Pathline yet |

## Crate reality vs Pathline bridge

Upstream `rsiprtp` documents **SRTP with SDES** (RFC 3711 + RFC 4568) for traditional
SIP carriers (not DTLS-SRTP / WebRTC). Pathline’s bridge still negotiates and sends
**plain RTP only**, and the env gate refuses non-lab profiles with:

> Production SIP requires SDES-SRTP media. Pathline currently offers plain RTP
> only for the loopback Asterisk lab...

That message is **Pathline-integration accurate today** (we do not enable SRTP),
even if the crate surface advertises SDES-SRTP. Treat enabling SRTP as an
**integration spike**, not a stack swap.

## Lab scaffolding landed

`scripts/lab-sip-setup.sh` accepts:

```bash
LAB_SIP_MEDIA_ENCRYPTION=sdes ./scripts/lab-sip-setup.sh
```

When set, the generated PJSIP endpoint includes:

```ini
media_encryption=sdes
media_encryption_optimistic=no
```

This is intentionally **not** the default and is not production readiness. It is
only an Asterisk-side switch for validating SRTP-required lab configuration with
an SRTP-capable test endpoint while the native Pathline bridge remains blocked
on SDES offer/answer and RTP encryption/decryption wiring.

## Smallest path to production fail-open (preferred)

Stay on locked `rsiprtp` (or a pin-compatible newer `0.4.x` after audit):

1. **Spike (lab first):** enable SDES-SRTP offer/answer in `run_call` SDP + RTP session
   against Asterisk with `LAB_SIP_MEDIA_ENCRYPTION=sdes`; keep
   `PATHLINE_SIP_PROFILE=lab` for plain RTP.
2. **New profile:** `PATHLINE_SIP_PROFILE=production` (or unset) requires SRTP; plain RTP
   remains lab+loopback only.
3. **Prove:** dial lab with SRTP → RTP → Whisper → DTMF → encrypted callstate.
4. **Trunk:** configure production ITSP with SDES-SRTP; set real SIP creds +
   `PATHLINE_SIP_VERIFY_TLS=1`; never relax TLS verify off-loopback.
5. **Update** this doc + `docs/production-acceptance.md` when SRTP lab proof lands;
   only then relax the fail-closed string in `SipConfig::from_env`.

## Contingency (only if spike fails)

If `rsiprtp` SDES-SRTP cannot be wired safely:

- Sanctioned pure-Rust fallback from `docs/desktop-sip-stack.md`:
  `rsipstack` + `rtp-engine`, or evaluate `rvoip-rtp-core` SDES-SRTP **behind** the
  same `NativeSipBridge` boundary (no engine/UI rewrite).
- **Rejected for v1 unless owner overturns lock:** Linphone / PJSIP FFI.

## Explicit non-goals

- DTLS-SRTP / browser WebRTC interop
- Shipping plain RTP to a public trunk
- Trusting the ITSP with audio/transcripts (audio stays on device regardless)

## Operator checklist before a real trunk

- [ ] Lab SRTP acceptance run recorded (`LAB_SIP_MEDIA_ENCRYPTION=sdes`)
- [ ] Trunk supports SDES-SRTP + SIP/TLS
- [ ] Release build sets `PATHLINE_API_URL` (HTTPS)
- [ ] Signed/notarized macOS DMG (Apple credentials)
