import Foundation

public enum WrapperMode: String, CaseIterable, Identifiable {
    case map = "Map"
    case replay = "Replay"
    case dryRun = "Dry Run"

    public var id: String { rawValue }
}

@MainActor
public final class NavigationState: ObservableObject {
    @Published public var selectedMode: WrapperMode = .map

    public init() {}
}