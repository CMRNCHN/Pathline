import Foundation

// ── Asterisk ARI wiring — the entire runtime ──────────────────────────────────
//
// WebSocket (/ari/events)  → typed events in
// HTTP (/ari/channels)     → call actions out
// No cloud, no Twilio, no Deepgram — just a local Asterisk instance.

/// Minimal typed decode of an ARI event. String-scanning JSON breaks silently on
/// schema/whitespace changes; this fails loudly (decode returns nil) and only on
/// the fields we actually use. Verified against the ARI events reference:
/// channel events carry `channel.id`; ChannelDtmfReceived carries `digit`.
private struct ARIEvent: Decodable {
    let type: String
    let channel: Channel?
    let digit: String?

    struct Channel: Decodable { let id: String? }
}

final class AsteriskClient: NSObject {

    // Local Asterisk ARI. `ari:ari` is the stock dev user:pass. All four are
    // overridable via PULSE_ARI_* env vars (see PulseConfig) so Pulse can target
    // a remote or non-default Asterisk without a rebuild.
    private let host = PulseConfig.host
    private let port = PulseConfig.port
    private let apiKey = PulseConfig.apiKey
    private let app = PulseConfig.app

    /// Silence (ms) before TALK_DETECT decides a prompt has ended and fires
    /// ChannelTalkingFinished. This is the FSM's one timing knob — it relocates
    /// the old hard-coded delays into a DSP threshold. NEEDS CALIBRATION against
    /// real IVR traffic: too low trips mid-prompt on natural pauses, too high
    /// adds latency before each DTMF send. (Asterisk default is 2500.)
    /// Override at runtime with PULSE_TALK_SILENCE_MS.
    private let talkSilenceMs = PulseConfig.talkSilenceMs

    /// A real prompt is a sustained speech segment. Multi-sentence prompts
    /// ("Enter your card number." <pause> "Followed by pound.") can make
    /// TALK_DETECT fire ChannelTalkingFinished after the first short sentence —
    /// which would send DTMF before the IVR is ready. We only advance the FSM
    /// when the talking segment lasted at least this long; shorter blips are
    /// ignored as mid-prompt pauses. NEEDS CALIBRATION against real traffic.
    /// Override at runtime with PULSE_MIN_PROMPT_MS.
    private let minimumPromptDurationMs: Double = PulseConfig.minimumPromptDurationMs

    /// channel.id → when its current talking segment began (ChannelTalkingStarted).
    private var talkingStartedAt: [String: Date] = [:]

    private var socket: URLSessionWebSocketTask?
    private let state: PulseState

    init(state: PulseState) {
        self.state = state
    }

    // MARK: - Connect ARI WebSocket

    func connect() {
        let url = URL(string: "ws://\(host):\(port)/ari/events?api_key=\(apiKey)&app=\(app)")!
        let task = URLSession(configuration: .default).webSocketTask(with: url)
        socket = task
        task.resume()
        listen()
    }

    private func listen() {
        socket?.receive { [weak self] result in
            guard let self else { return }
            if case .success(let message) = result {
                self.handle(message)
                self.listen()   // re-arm for the next frame
            }
            // On failure we stop listening (no retry — intentional).
        }
    }

    // MARK: - Event router (typed)

    private func handle(_ message: URLSessionWebSocketTask.Message) {
        guard
            case .string(let text) = message,
            let data = text.data(using: .utf8),
            let event = try? JSONDecoder().decode(ARIEvent.self, from: data)
        else { return }

        // Hop to main — PulseState is @MainActor.
        Task { @MainActor in self.apply(event) }
    }

    @MainActor
    private func apply(_ event: ARIEvent) {
        guard let id = event.channel?.id, state.owns(id) else { return }

        switch event.type {
        case "StasisStart":
            state.enterStasis(channelId: id)
            enableTalkDetect(channelId: id)      // arm prompt-end detection
        case "ChannelTalkingStarted":
            talkingStartedAt[id] = Date()
        case "ChannelTalkingFinished":
            if promptWasLongEnough(id) {
                perform(state.advance(channelId: id), on: id)
            }
        case "ChannelDtmfReceived":
            if let digit = event.digit { state.noteDTMF(channelId: id, digit: digit) }
        case "ChannelDestroyed":
            talkingStartedAt[id] = nil
            state.finish(channelId: id)
        default:
            break
        }
    }

    /// True if the talking segment that just ended was a real prompt, not a
    /// mid-prompt pause. Fails open: if we never saw the matching Started, we
    /// advance rather than stall the probe.
    private func promptWasLongEnough(_ channelId: String) -> Bool {
        defer { talkingStartedAt[channelId] = nil }
        guard let started = talkingStartedAt[channelId] else { return true }
        return Date().timeIntervalSince(started) * 1000 >= minimumPromptDurationMs
    }

    private func perform(_ action: ProbeAction, on channelId: String) {
        switch action {
        case .sendDTMF(let digits): sendDTMF(channelId: channelId, digits: digits)
        case .hangup:               hangup(channelId: channelId)
        case .none:                 break
        }
    }

    // MARK: - Actions (ARI HTTP control)

    /// Originate, assigning our pre-reserved channel id so events route deterministically.
    func placeCall(to number: String, channelId: String) {
        fire("/ari/channels", method: "POST", query: [
            "endpoint": "PJSIP/\(number)",
            "app": app,
            "channelId": channelId,
        ])
    }

    /// Enable TALK_DETECT so the channel raises ChannelTalkingStarted/Finished.
    private func enableTalkDetect(channelId: String) {
        fire("/ari/channels/\(channelId)/variable", method: "POST", query: [
            "variable": "TALK_DETECT(set)",
            "value": "\(talkSilenceMs)",
        ])
    }

    func sendDTMF(channelId: String, digits: String) {
        fire("/ari/channels/\(channelId)/dtmf", method: "POST", query: ["dtmf": digits])
    }

    func hangup(channelId: String) {
        fire("/ari/channels/\(channelId)", method: "DELETE")
    }

    // MARK: - Request builder

    /// Fire-and-forget HTTP. Uses URLComponents so values like `TALK_DETECT(set)`
    /// and `**11` are percent-encoded correctly. Every call carries api_key, or
    /// Asterisk answers 401.
    private func fire(_ path: String, method: String, query: [String: String] = [:]) {
        var comps = URLComponents()
        comps.scheme = "http"
        comps.host = host
        comps.port = port
        comps.path = path
        comps.queryItems =
            query.map { URLQueryItem(name: $0.key, value: $0.value) }
            + [URLQueryItem(name: "api_key", value: apiKey)]
        guard let url = comps.url else { return }

        var req = URLRequest(url: url)
        req.httpMethod = method
        URLSession.shared.dataTask(with: req).resume()
    }
}
