import SwiftUI

struct MenuBarView: View {
    @State var isRecording = false

    var body: some View {
        VStack {
            Text(isRecording ? "Recording" : "Idle")
            Button("Toggle") { isRecording.toggle() }
        }
    }
}
