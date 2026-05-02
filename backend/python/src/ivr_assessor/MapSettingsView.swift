import SwiftUI

public struct MapSettingsView: View {
    @ObservedObject var viewModel: MapSessionViewModel

    public var body: some View {
        Form {
            Section(header: Text("Session Configuration")) {
                TextField("Target Phone Number", text: $viewModel.targetNumber)

                Picker("Session Mode", selection: $viewModel.sessionMode) {
                    ForEach(SessionMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }

                Picker("Response Mode", selection: $viewModel.responseMode) {
                    ForEach(ResponseMode.allCases, id: \.self) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
            }

            Button(action: {
                viewModel.startMap()
            }) {
                HStack {
                    Image(systemName: "play.fill")
                    Text("Start Mapping Session")
                }
            }
            .disabled(viewModel.targetNumber.isEmpty || viewModel.isRunning)
            .keyboardShortcut(.defaultAction)
        }
        .padding()
    }
}