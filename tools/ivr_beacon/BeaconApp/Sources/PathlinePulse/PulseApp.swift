import SwiftUI

// ── Menu bar UI + trigger — no flow logic, no timers ──────────────────────────
//
// This layer only starts a probe. All progression is driven by ARI events in
// AsteriskClient → PulseState's FSM. There is intentionally no asyncAfter here.

@main
struct PulseApp: App {
    @StateObject private var state = PulseState()
    @State private var client: AsteriskClient?

    // Probe definition. Defaults run against a stock setup; override via the
    // PULSE_* environment variables (see PulseConfig / README) to point at your
    // own IVR without recompiling. The suite-as-script engine remains a non-goal.
    private let target = PulseConfig.target
    private let menuDigits = PulseConfig.menuDigits
    private let cardDigits = PulseConfig.cardDigits

    var body: some Scene {
        MenuBarExtra("Pulse", systemImage: "waveform.path.ecg") {
            VStack(alignment: .leading, spacing: 12) {
                Button("Run Probe") { runProbe() }

                Divider()

                if state.probes.isEmpty {
                    Text("No probes yet")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(state.probes) { probe in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(probe.targetNumber).font(.headline)
                            Text("\(probe.status.rawValue) · \(probe.phase.rawValue)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            if !probe.transcript.isEmpty {
                                Text(probe.transcript)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(6)
                    }
                }
            }
            .padding(12)
            .frame(width: 260)
            .task { ensureConnected() }
        }
        .menuBarExtraStyle(.window)
    }

    /// Connect on first appearance, exactly once.
    private func ensureConnected() {
        guard client == nil else { return }
        let c = AsteriskClient(state: state)
        c.connect()
        client = c
    }

    /// Start one probe. The channel id is reserved here and handed to ARI, so the
    /// event stream is bound to this probe from the first frame.
    private func runProbe() {
        let channelId = state.startProbe(number: target, menu: menuDigits, card: cardDigits)
        client?.placeCall(to: target, channelId: channelId)
    }
}
