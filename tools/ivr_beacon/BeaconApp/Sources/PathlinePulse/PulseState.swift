import Foundation

// ── Single source of truth ────────────────────────────────────────────────────

enum CallStatus: String {
    case connecting
    case inCall
    case completed
    case error
}

/// Liveness of the ARI WebSocket. Surfaced in the menu bar so a failed or
/// dropped connection is visible instead of silent — the app used to connect
/// once and show nothing, which made "why isn't anything happening?" unanswerable.
enum ConnectionState: String {
    case connecting = "connecting…"
    case connected = "connected"
    case disconnected = "disconnected"
}

/// The four phases of a card-status probe — "what we are waiting for".
/// Not a general workflow engine: call → greeting → card prompt → result → done.
/// Sends (menu DTMF, card DTMF) are `ProbeAction`s, not phases — in an
/// event-driven model a send is the transition between two waits, not a state.
enum ProbePhase: String {
    case waitingForGreeting     // call placed; awaiting answer + IVR greeting
    case waitingForCardPrompt   // menu selection sent; awaiting card prompt
    case waitingForResult       // card sent; awaiting result prompt
    case done
}

/// The side effect a transition asks the client to perform. Pure data — the
/// FSM decides, `AsteriskClient` executes the I/O.
enum ProbeAction: Equatable {
    case none
    case sendDTMF(String)
    case hangup
}

struct CallProbe: Identifiable {
    let id = UUID()
    let targetNumber: String
    let menuDigits: String   // DTMF sent after the greeting
    let cardDigits: String   // DTMF sent after the card prompt
    var status: CallStatus = .connecting
    var phase: ProbePhase = .waitingForGreeting
    var transcript: String = ""
}

/// The only mutable state. @MainActor — every mutation lands on the main thread,
/// so the menu bar UI observes a consistent snapshot.
///
/// Routing rule (production-critical): every update is addressed by ARI
/// `channel.id`, never by an implicit "active" probe. `channelMap` is the sole
/// channel.id → probe binding; events for channels we don't own (e.g. a bridged
/// second leg from a transfer) resolve to nothing and are ignored. This is what
/// prevents DTMF reaching the wrong call and transcripts merging across probes.
@MainActor
final class PulseState: ObservableObject {
    @Published private(set) var probes: [CallProbe] = []

    /// ARI WebSocket liveness, for the menu bar status line.
    @Published private(set) var connection: ConnectionState = .connecting

    /// ARI channel.id → CallProbe.id. The one source of channel ownership.
    private(set) var channelMap: [String: UUID] = [:]

    /// Update the displayed ARI connection state. Called by AsteriskClient as the
    /// WebSocket opens, closes, or drops.
    func setConnection(_ state: ConnectionState) { connection = state }

    /// Append a diagnostic line to a probe's transcript — armed TALK_DETECT,
    /// prompt boundaries, ignored blips — so the operator can see *why* the FSM
    /// is (or isn't) advancing, not just its final state.
    func note(channelId: String, _ line: String) {
        guard let i = index(for: channelId) else { return }
        appendTranscript(&probes[i], line)
    }

    /// Create a probe and reserve its channel id up front. We hand this id to
    /// ARI on originate (`channelId`), so the binding exists *before* any event
    /// arrives — StasisStart can never race ahead of the mapping.
    /// Returns the channel id to originate with.
    func startProbe(number: String, menu: String, card: String) -> String {
        let probe = CallProbe(targetNumber: number, menuDigits: menu, cardDigits: card)
        let channelId = probe.id.uuidString
        probes.append(probe)
        channelMap[channelId] = probe.id
        return channelId
    }

    /// Do we own this channel? Used to ignore foreign channels (bridges/transfers).
    func owns(_ channelId: String) -> Bool { channelMap[channelId] != nil }

    /// StasisStart: the call is up and in our Stasis app. Phase is already
    /// `.waitingForGreeting` from creation — we just mark it in-call.
    func enterStasis(channelId: String) {
        guard let i = index(for: channelId) else { return }
        probes[i].status = .inCall
    }

    /// A prompt just ended (and passed the duration guard) → advance the FSM and
    /// tell the client what I/O to perform. Pure transition; no timing here.
    func advance(channelId: String) -> ProbeAction {
        guard let i = index(for: channelId) else { return .none }
        switch probes[i].phase {
        case .waitingForGreeting:
            probes[i].phase = .waitingForCardPrompt
            appendTranscript(&probes[i], "→ menu \(probes[i].menuDigits)")
            return .sendDTMF(probes[i].menuDigits)
        case .waitingForCardPrompt:
            probes[i].phase = .waitingForResult
            // Hand the PAN off to the client, then wipe it from app memory
            // immediately. After this point the card number lives nowhere in
            // Pulse — not in the probe, not in the transcript (we log only the
            // digit count). This bounds PAN residency to a single FSM transition.
            let card = probes[i].cardDigits
            probes[i].cardDigits = ""
            appendTranscript(&probes[i], "→ card (\(card.count) digits)")
            return .sendDTMF(card)
        case .waitingForResult:
            probes[i].phase = .done
            appendTranscript(&probes[i], "→ hangup")
            return .hangup
        case .done:
            return .none
        }
    }

    /// A DTMF digit was received on the channel. We deliberately do NOT record
    /// the digit's *value*: during the card phase the IVR (or a loopback echo)
    /// can emit the card number digit-by-digit, and logging each value would
    /// reconstruct the full PAN in the transcript — a cardholder-data leak into
    /// both the UI and process memory. We log only that a digit arrived, which
    /// preserves the diagnostic ("DTMF is flowing") without the sensitive value.
    /// Digits Pulse *sends* are already shown structurally in `advance()` (menu
    /// verbatim, card as a count only).
    func noteDTMF(channelId: String, digit _: String) {
        guard let i = index(for: channelId) else { return }
        appendTranscript(&probes[i], "‹dtmf received›")
    }

    /// ChannelDestroyed: the call ended (by us or the far side).
    func finish(channelId: String) {
        guard let i = index(for: channelId) else { return }
        probes[i].status = .completed
        probes[i].phase = .done
    }

    // MARK: - Internals

    private func index(for channelId: String) -> Int? {
        guard let probeId = channelMap[channelId] else { return nil }
        return probes.firstIndex { $0.id == probeId }
    }

    private func appendTranscript(_ probe: inout CallProbe, _ line: String) {
        probe.transcript += probe.transcript.isEmpty ? line : "\n\(line)"
    }
}
