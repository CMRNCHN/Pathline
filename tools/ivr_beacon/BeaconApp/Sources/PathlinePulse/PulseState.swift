import Foundation

// ── Single source of truth ────────────────────────────────────────────────────

enum CallStatus: String {
    case connecting
    case inCall
    case completed
    case error
}

/// Resting states of the probe FSM — "what we are waiting for".
///
/// The user's spec also listed `sendMenuDTMF` / `sendCard`. In an event-driven
/// model a send is a *transition action*, not a state you rest in: each
/// `ChannelTalkingFinished` performs the pending send and settles into the next
/// `wait`. Those two are therefore `ProbeAction` cases, not `ProbeStep` cases.
enum ProbeStep: String {
    case start
    case waitGreeting       // call answered, IVR greeting playing
    case waitCardPrompt     // menu selection sent, awaiting card prompt
    case waitResult         // card sent, awaiting result prompt
    case end
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
    var step: ProbeStep = .start
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

    /// StasisStart: the call is up and in our Stasis app.
    func enterStasis(channelId: String) {
        guard let i = index(for: channelId) else { return }
        probes[i].status = .inCall
        probes[i].step = .waitGreeting
    }

    /// ChannelTalkingFinished: a prompt just ended → advance the FSM and tell the
    /// client what I/O to perform. Pure transition; the only timing assumption
    /// (silence threshold) lives in TALK_DETECT, not here.
    func advance(channelId: String) -> ProbeAction {
        guard let i = index(for: channelId) else { return .none }
        switch probes[i].step {
        case .waitGreeting:
            probes[i].step = .waitCardPrompt
            appendTranscript(&probes[i], "→ menu \(probes[i].menuDigits)")
            return .sendDTMF(probes[i].menuDigits)
        case .waitCardPrompt:
            probes[i].step = .waitResult
            appendTranscript(&probes[i], "→ card (\(probes[i].cardDigits.count) digits)")
            return .sendDTMF(probes[i].cardDigits)
        case .waitResult:
            probes[i].step = .end
            appendTranscript(&probes[i], "→ hangup")
            return .hangup
        case .start, .end:
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
        probes[i].step = .end
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
