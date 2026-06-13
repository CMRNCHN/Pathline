import Foundation

// ── Runtime configuration ─────────────────────────────────────────────────────
//
// Every tunable Pulse has lives here, each with a default that makes the app run
// with zero configuration against a stock local Asterisk. Any value can be
// overridden via an environment variable, so a tester can point Pulse at their
// own IVR, a remote Asterisk, or calibrate prompt-boundary timing — all without
// recompiling. This is what makes Pulse testable against real IVR traffic before
// the timing knobs below are calibrated.
//
// This is configuration, not the suite-as-script engine: it reads three fixed
// probe values, it does not interpret a scenario file. That engine remains a
// deliberate non-goal until Pulse runs against real Asterisk traffic.
enum PulseConfig {
    private static let env = ProcessInfo.processInfo.environment

    private static func string(_ key: String, _ fallback: String) -> String {
        guard let v = env[key], !v.isEmpty else { return fallback }
        return v
    }

    private static func int(_ key: String, _ fallback: Int) -> Int {
        guard let v = env[key], let n = Int(v) else { return fallback }
        return n
    }

    private static func double(_ key: String, _ fallback: Double) -> Double {
        guard let v = env[key], let n = Double(v) else { return fallback }
        return n
    }

    // ── Probe definition ──────────────────────────────────────────────────────
    // cardDigits has NO default on purpose: a card number is entered per-run in
    // the menu bar, never baked into source or pre-filled into the field. This
    // keeps even a card-shaped placeholder out of the binary and off the screen.
    // PULSE_CARD_DIGITS still works for an automated/loopback test if you set it,
    // but the privacy-correct path is to leave it unset and type the card in.
    static var target: String { string("PULSE_TARGET", "+18009505114") }
    static var menuDigits: String { string("PULSE_MENU_DIGITS", "**11") }
    static var cardDigits: String { string("PULSE_CARD_DIGITS", "") }

    /// The ARI originate endpoint. Defaults to a PJSIP trunk call to `target`
    /// (the production path), so behavior is unchanged when unset. Override with
    /// PULSE_ENDPOINT to dial something else — e.g. "Local/1000@ivr-test" to loop
    /// against the test container's built-in IVR with no carrier or trunk.
    static var endpoint: String { string("PULSE_ENDPOINT", "PJSIP/\(target)") }

    // ── Asterisk ARI connection ───────────────────────────────────────────────
    // `ari:ari` is the stock dev user:pass; override for any real instance.
    static var host: String { string("PULSE_ARI_HOST", "127.0.0.1") }
    static var port: Int { int("PULSE_ARI_PORT", 8088) }
    static var apiKey: String { string("PULSE_ARI_API_KEY", "ari:ari") }
    static var app: String { string("PULSE_ARI_APP", "pulse") }

    // ── Prompt-boundary timing (NEEDS CALIBRATION) ────────────────────────────
    // See AsteriskClient for the full rationale on these two knobs. They are
    // surfaced as env vars precisely so they can be calibrated against real
    // traffic without a rebuild.
    static var talkSilenceMs: Int { int("PULSE_TALK_SILENCE_MS", 1500) }
    static var minimumPromptDurationMs: Double { double("PULSE_MIN_PROMPT_MS", 2000) }
}
