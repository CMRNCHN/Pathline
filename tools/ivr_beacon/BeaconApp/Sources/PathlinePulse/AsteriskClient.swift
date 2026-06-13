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

    /// channel.id → the mixing bridge we created to hold it. The control channel
    /// must be in a bridge for its media to be pumped, otherwise TALK_DETECT never
    /// sees audio on a loopback (Local) call and the FSM stalls. See enterStasis.
    private var bridges: [String: String] = [:]

    private var socket: URLSessionWebSocketTask?
    private lazy var session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    private var reconnecting = false
    private let state: PulseState

    init(state: PulseState) {
        self.state = state
    }

    // MARK: - Connect ARI WebSocket

    func connect() {
        Task { @MainActor in self.state.setConnection(.connecting) }
        let url = URL(string: "ws://\(host):\(port)/ari/events?api_key=\(apiKey)&app=\(app)")!
        let task = session.webSocketTask(with: url)
        socket = task
        task.resume()
        listen()
    }

    private func listen() {
        socket?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                self.handle(message)
                self.listen()   // re-arm for the next frame
            case .failure:
                // The read failed (ARI down, dropped). Surface it and retry —
                // the old client died silently here, which is why a probe could
                // look frozen with no explanation.
                Task { @MainActor in self.state.setConnection(.disconnected) }
                self.scheduleReconnect()
            }
        }
    }

    /// Reconnect once after a short delay. Guarded so the delegate's close/error
    /// callbacks and a failed read don't stack up multiple reconnect loops.
    private func scheduleReconnect() {
        guard !reconnecting else { return }
        reconnecting = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            self?.reconnecting = false
            self?.connect()
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
            // Hold the channel in a mixing bridge so Asterisk pumps its media —
            // without this, TALK_DETECT gets no audio on a Local loopback call and
            // no prompt-end ever fires. Then arm prompt-end detection.
            let bridgeId = "\(id)-bridge"
            bridges[id] = bridgeId
            createBridge(bridgeId)
            addToBridge(bridgeId: bridgeId, channelId: id)
            enableTalkDetect(channelId: id)
            state.note(channelId: id, "⚙ stasis · bridged · talk-detect \(talkSilenceMs)ms")
        case "ChannelTalkingStarted":
            talkingStartedAt[id] = Date()
            state.note(channelId: id, "▸ prompt started")
        case "ChannelTalkingFinished":
            if promptWasLongEnough(id) {
                perform(state.advance(channelId: id), on: id)
            } else {
                state.note(channelId: id, "· short blip ignored")
            }
        case "ChannelDtmfReceived":
            if let digit = event.digit { state.noteDTMF(channelId: id, digit: digit) }
        case "ChannelDestroyed":
            talkingStartedAt[id] = nil
            if let bridgeId = bridges.removeValue(forKey: id) { destroyBridge(bridgeId) }
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

    /// Originate, assigning our pre-reserved channel id so events route
    /// deterministically. `endpoint` is the full ARI endpoint string (e.g.
    /// "PJSIP/+18005551234" or "Local/1000@ivr-test"); see PulseConfig.endpoint.
    func placeCall(endpoint: String, channelId: String) {
        fire("/ari/channels", method: "POST", query: [
            "endpoint": endpoint,
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

    /// Send DTMF on the channel. ⚠️ CARDHOLDER DATA: when `digits` is the card
    /// number, it rides in the request URL's query string (ARI takes `dtmf` as a
    /// query param). This client speaks cleartext `http://`, which is safe ONLY on
    /// loopback, where the request never reaches a wire. If you ever point Pulse
    /// at a non-loopback `PULSE_ARI_HOST`, you MUST terminate ARI over TLS first —
    /// otherwise the PAN travels in cleartext and can land in any intermediary's
    /// access log. Keep ARI on 127.0.0.1 (default) unless TLS is in place.
    func sendDTMF(channelId: String, digits: String) {
        fire("/ari/channels/\(channelId)/dtmf", method: "POST", query: ["dtmf": digits])
    }

    func hangup(channelId: String) {
        fire("/ari/channels/\(channelId)", method: "DELETE")
    }

    // MARK: - Bridge (media pumping for TALK_DETECT)

    /// Create a mixing bridge with a pre-chosen id (so we never need to parse the
    /// POST response — same trick as the pre-reserved channel id).
    private func createBridge(_ bridgeId: String) {
        fire("/ari/bridges/\(bridgeId)", method: "POST", query: ["type": "mixing"])
    }

    private func addToBridge(bridgeId: String, channelId: String) {
        fire("/ari/bridges/\(bridgeId)/addChannel", method: "POST", query: ["channel": channelId])
    }

    private func destroyBridge(_ bridgeId: String) {
        fire("/ari/bridges/\(bridgeId)", method: "DELETE")
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

// MARK: - WebSocket lifecycle → connection state

extension AsteriskClient: URLSessionWebSocketDelegate {
    func urlSession(_ session: URLSession,
                    webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol protocol: String?) {
        Task { @MainActor in self.state.setConnection(.connected) }
    }

    func urlSession(_ session: URLSession,
                    webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
                    reason: Data?) {
        Task { @MainActor in self.state.setConnection(.disconnected) }
        scheduleReconnect()
    }
}
