import SwiftUI
import IVRWrapperCore

struct ContentView: View {
    @EnvironmentObject var navigation: NavigationState
    @ObservedObject var viewModel: MapSessionViewModel

    var body: some View {
        NavigationSplitView {
            List(WrapperMode.allCases, selection: $navigation.selectedMode) { mode in
                NavigationLink(value: mode) {
                    Label(mode.rawValue, systemImage: icon(for: mode))
                }
            }
            .navigationSplitViewColumnWidth(min: 180, ideal: 200)
        } content: {
            // This would switch based on navigation.selectedMode
            MapSettingsView(viewModel: viewModel)
                .navigationSplitViewColumnWidth(min: 300, ideal: 350)
        } detail: {
            // This would also switch based on navigation.selectedMode
            SessionResultsView(viewModel: viewModel)
        }
        .navigationTitle("IVR Assessor")
    }

    private func icon(for mode: WrapperMode) -> String {
        switch mode {
        case .map:
            return "map"
        case .replay:
            return "backward.end.alt"
        case .dryRun:
            return "text.clipboard"
        }
    }
}