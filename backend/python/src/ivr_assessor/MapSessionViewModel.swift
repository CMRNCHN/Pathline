import Foundation

@MainActor
public final class MapSessionViewModel: ObservableObject {
    // MARK: - Inputs
    @Published public var targetNumber: String = ""
    @Published public var sessionMode: SessionMode = .singleSession
    @Published public var responseMode: ResponseMode = .dtmf

    // MARK: - Outputs
    @Published public private(set) var sessions: [SessionRecord] = []
    @Published public private(set) var statusText: String = "Idle"
    @Published public var isRunning: Bool = false

    private let store: SessionStore

    public init(store: SessionStore) {
        self.store = store
    }

    public func startMap() {
        let request = MapRequest(
            targetNumbers: [targetNumber],
            sessionMode: sessionMode,
            responseMode: responseMode
        )

        // In a real implementation, this would call the PythonCLIClient
        // For now, we'll simulate a running state.
        self.isRunning = true
        self.statusText = "Starting session for \(targetNumber)..."
        self.sessions = [
            SessionRecord(
                id: "session-1",
                targetNumber: targetNumber,
                sessionMode: sessionMode,
                statusText: "In Progress",
                graphSummary: "Mapping..."
            )
        ]
    }
}