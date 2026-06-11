import Foundation

// ── Single source of truth ────────────────────────────────────────────────────

enum CallStatus: String {
    case connecting
    case inCall
    case completed
    case error
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

    /// ARI channel.id → CallProbe.id. The one source of channel ownership.
    private(set) var channelMap: [String: UUID] = [:]

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
            appendTranscript(&probes[i], "→ card (\(probes[i].cardDigits.count) digits)")
            return .sendDTMF(probes[i].cardDigits)
        case .waitingForResult:
            probes[i].phase = .done
            appendTranscript(&probes[i], "→ hangup")
            return .hangup
        case .done:
            return .none
        }
    }

    func noteDTMF(channelId: String, digit: String) {
        guard let i = index(for: channelId) else { return }
        appendTranscript(&probes[i], "‹dtmf \(digit)›")
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
