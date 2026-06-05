import SwiftUI

@main
struct PathlinePulseApp: App {
    @StateObject private var store = JobStore()

    var body: some Scene {
        // ── Menu bar icon + dropdown ──────────────────────────────────────────
        MenuBarExtra {
            PulseMenuView()
                .environmentObject(store)
                .frame(width: 310)
        } label: {
            MenuBarLabel(store: store)
        }
        .menuBarExtraStyle(.window)

        // ── Full floating window (opened from dropdown) ───────────────────────
        Window("Pathline Pulse", id: "pulse-window") {
            FullWindowView()
                .environmentObject(store)
        }
        .defaultSize(width: 780, height: 520)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
    }
}

// ── Menu bar icon — pulses when any job is RED or ORANGE ──────────────────────

private struct MenuBarLabel: View {
    @ObservedObject var store: JobStore

    private var urgentColor: Color? {
        if store.jobs.contains(where: { $0.status.uppercased() == "RED" })    { return .red }
        if store.jobs.contains(where: { $0.status.uppercased() == "ORANGE" }) { return .orange }
        return nil
    }

    var body: some View {
        Image(systemName: "waveform.path.ecg")
            .symbolEffect(.pulse, options: .repeating, isActive: urgentColor != nil)
            .foregroundStyle(urgentColor ?? .primary)
    }
}
