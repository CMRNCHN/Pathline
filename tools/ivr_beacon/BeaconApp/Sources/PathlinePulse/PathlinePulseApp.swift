import SwiftUI

// ── Dependency graph — built once, injected everywhere ────────────────────────

@MainActor
final class AppContainer: ObservableObject {
    let notifications = NotificationService()
    let store: JobStore
    let service = JobService()
    let runner = JobRunner()
    private var watcher: JobWatcher?

    init() {
        store = JobStore(notifications: notifications)
        notifications.requestPermissionIfNeeded()
        watcher = JobWatcher(store: store)
    }
}

// ── App ───────────────────────────────────────────────────────────────────────

@main
struct PathlinePulseApp: App {
    @StateObject private var container = AppContainer()

    var body: some Scene {
        MenuBarExtra {
            PulseMenuView()
                .environmentObject(container.store)
                .environmentObject(container.service)
                .frame(width: 310)
        } label: {
            MenuBarLabel(store: container.store)
        }
        .menuBarExtraStyle(.window)

        Window("Pathline Pulse", id: "pulse-window") {
            FullWindowView()
                .environmentObject(container.store)
                .environmentObject(container.runner)
                .environmentObject(container.service)
        }
        .defaultSize(width: 780, height: 520)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
    }
}

// ── Menu bar icon — 4 states: healthy / running / warning / failed ────────────

private struct MenuBarLabel: View {
    @ObservedObject var store: JobStore

    private var iconState: IconState {
        if store.isRunning { return .running }
        let statuses = store.jobs.map { $0.status.uppercased() }
        if statuses.contains("RED")              { return .failed }
        if statuses.contains("ORANGE") || statuses.contains("YELLOW") { return .warning }
        if !store.jobs.isEmpty                   { return .healthy }
        return .idle
    }

    var body: some View {
        Image(systemName: iconState.symbolName)
            .symbolEffect(.pulse, options: .repeating, isActive: iconState == .running)
            .foregroundStyle(iconState.color)
    }

    private enum IconState: Equatable {
        case idle, healthy, running, warning, failed

        var symbolName: String {
            switch self {
            case .idle:    return "waveform.path.ecg"
            case .healthy: return "waveform.path.ecg"
            case .running: return "waveform.path.ecg.rectangle"
            case .warning: return "exclamationmark.triangle"
            case .failed:  return "waveform.path.ecg"
            }
        }

        var color: Color {
            switch self {
            case .idle:    return .secondary
            case .healthy: return .green
            case .running: return .blue
            case .warning: return .orange
            case .failed:  return .red
            }
        }
    }
}
