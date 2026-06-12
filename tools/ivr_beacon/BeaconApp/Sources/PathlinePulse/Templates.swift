import Foundation

// ── Probe templates ───────────────────────────────────────────────────────────
//
// A template is a named preset the operator picks from the menu bar: where to
// call and how to reach the card prompt. This is deliberately NOT a scripting
// engine — it is a fixed bundle of fields. The card number is never part of a
// template; it is entered per run (a card is data, not configuration).

/// One selectable preset. Codable so users can ship their own without a rebuild.
struct ProbeTemplate: Identifiable, Hashable, Codable {
    let id: String
    let name: String      // shown in the picker
    let endpoint: String  // ARI originate endpoint, e.g. "PJSIP/+1800…" or "Local/1000@ivr-test/n"
    let target: String    // display label for the probe row
    let menuDigits: String // DTMF sent after the greeting
}

enum ProbeTemplates {
    /// Everything offered in the picker: the live PULSE_* environment first (so
    /// env-var driven runs still work), then user-defined templates if present,
    /// otherwise the built-ins.
    static var all: [ProbeTemplate] {
        [environment] + userDefinedOrBuiltins
    }

    /// Mirrors whatever PULSE_* env vars are set, so the existing override path is
    /// just another template.
    static var environment: ProbeTemplate {
        ProbeTemplate(
            id: "environment",
            name: "Environment (PULSE_*)",
            endpoint: PulseConfig.endpoint,
            target: PulseConfig.target,
            menuDigits: PulseConfig.menuDigits
        )
    }

    /// Load `[ProbeTemplate]` from a JSON file if one exists — PULSE_TEMPLATES, or
    /// ~/.pulse/templates.json — so operators can add their own IVRs. Falls back
    /// to the built-ins on any problem; never throws into the UI.
    private static var userDefinedOrBuiltins: [ProbeTemplate] {
        let env = ProcessInfo.processInfo.environment
        let home = (NSHomeDirectory() as NSString).appendingPathComponent(".pulse/templates.json")
        let path = env["PULSE_TEMPLATES"] ?? home
        if let data = FileManager.default.contents(atPath: path),
           let list = try? JSONDecoder().decode([ProbeTemplate].self, from: data),
           !list.isEmpty {
            return list
        }
        return builtins
    }

    static let builtins: [ProbeTemplate] = [
        ProbeTemplate(
            id: "local-test",
            name: "Local test IVR (container)",
            endpoint: "Local/1000@ivr-test/n",
            target: "Local/1000 · test IVR",
            menuDigits: "2"
        ),
        ProbeTemplate(
            id: "card-status",
            name: "Card status line",
            endpoint: "PJSIP/+18009505114",
            target: "+18009505114",
            menuDigits: "**11"
        ),
    ]
}

/// Mutable form state behind the menu bar controls — the chosen template and the
/// card number the operator typed. Held as a @StateObject so it survives the menu
/// opening and closing.
@MainActor
final class ProbeForm: ObservableObject {
    @Published var template: ProbeTemplate
    @Published var card: String

    init() {
        self.template = ProbeTemplates.all.first ?? ProbeTemplates.environment
        self.card = PulseConfig.cardDigits
    }
}
