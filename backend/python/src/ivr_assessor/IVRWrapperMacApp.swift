import SwiftUI
import IVRWrapperCore

@main
struct IVRWrapperMacApp: App {
    @StateObject private var store: SessionStore
    @StateObject private var navigationState: NavigationState
    @StateObject private var mapViewModel: MapSessionViewModel

    init() {
        let newStore = SessionStore()
        _store = StateObject(wrappedValue: newStore)
        _navigationState = StateObject(wrappedValue: NavigationState())
        _mapViewModel = StateObject(wrappedValue: MapSessionViewModel(store: newStore))
    }

    var body: some Scene {
        WindowGroup {
            ContentView(viewModel: mapViewModel)
                .environmentObject(navigationState)
        }
    }
}