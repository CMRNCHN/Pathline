import SwiftUI

// ── Menu bar UI + trigger — no flow logic, no timers ──────────────────────────
//
// This layer only starts a probe. All progression is driven by ARI events in
// AsteriskClient → PulseState's FSM. There is intentionally no asyncAfter here.

@main
struct PulseApp: App {
    @StateObject private var state = PulseState()
    @StateObject private var form = ProbeForm()
    @State private var client: AsteriskClient?

    var body: some Scene {
        MenuBarExtra("Pulse", systemImage: "waveform.path.ecg") {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(state.connection == .connected ? Color.green : Color.orange)
                        .frame(width: 8, height: 8)
                    Text("ARI: \(state.connection.rawValue)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Picker("Template", selection: $form.template) {
                    ForEach(ProbeTemplates.all) { template in
                        Text(template.name).tag(template)
                    }
                }
                .pickerStyle(.menu)

                HStack(spacing: 6) {
                    Text("Card").font(.caption).foregroundStyle(.secondary)
                    TextField("card number", text: $form.card)
                        .textFieldStyle(.roundedBorder)
                }

                Button("Run Probe") { runProbe() }
                    .disabled(state.connection != .connected || form.card.isEmpty)

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

    /// Start one probe from the selected template + typed card number. The channel
    /// id is reserved here and handed to ARI, so the event stream is bound to this
    /// probe from the first frame.
    private func runProbe() {
        let t = form.template
        let channelId = state.startProbe(number: t.target, menu: t.menuDigits, card: form.card)
        client?.placeCall(endpoint: t.endpoint, channelId: channelId)
    }
}
