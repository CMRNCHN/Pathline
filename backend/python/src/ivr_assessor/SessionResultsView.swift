import SwiftUI

public struct SessionResultsView: View {
    @ObservedObject var viewModel: MapSessionViewModel

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Session Output")
                .font(.headline)
                .padding([.horizontal, .top])

            List {
                if viewModel.sessions.isEmpty {
                    Text("No active session.")
                        .foregroundColor(.secondary)
                } else {
                    ForEach(viewModel.sessions) { session in
                        VStack(alignment: .leading) {
                            Text(session.targetNumber).font(.headline)
                            Text("Status: \(session.statusText)").font(.subheadline)
                            Text("Mode: \(session.sessionMode.rawValue)").font(.caption).foregroundColor(.secondary)
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Text(viewModel.statusText)
                .font(.caption.monospaced())
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(nsColor: .textBackgroundColor))
        }
    }
}