import SwiftUI

@main
struct IVRBeaconApp: App {
    var body: some Scene {
        WindowGroup("IVR Beacon") {
            ContentView()
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 760, height: 500)
    }
}
