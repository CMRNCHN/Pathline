import SwiftUI

struct FullWindowView: View {
    @EnvironmentObject var store: JobStore
    @State private var selectedJobID: String?

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            if let id = selectedJobID, let job = store.jobs.first(where: { $0.id == id }) {
                JobDetailView(job: job)
            } else {
                ContentUnavailableView(
                    "Select a Job",
                    systemImage: "waveform.path.ecg",
                    description: Text("Choose a job from the sidebar to view its details.")
                )
            }
        }
        .navigationTitle("Pathline Pulse")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    store.reload()
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .help("Refresh")
            }
        }
    }

    private var sidebar: some View {
        List(store.jobs, selection: $selectedJobID) { job in
            HStack(spacing: 10) {
                Circle()
                    .fill(job.statusColor)
                    .frame(width: 9, height: 9)
                VStack(alignment: .leading, spacing: 2) {
                    Text(job.name)
                        .font(.callout)
                    Text(job.relativeTime)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .tag(job.id)
            .padding(.vertical, 3)
        }
        .listStyle(.sidebar)
        .frame(minWidth: 180)
        .navigationSplitViewColumnWidth(min: 180, ideal: 200)
        .overlay {
            if store.jobs.isEmpty {
                VStack(spacing: 6) {
                    Image(systemName: "waveform.path.ecg")
                        .font(.title2)
                        .foregroundStyle(.tertiary)
                    Text("No results yet")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

// ── Job detail panel ──────────────────────────────────────────────────────────

private struct JobDetailView: View {
    let job: JobResult

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Status header
                HStack(spacing: 10) {
                    Circle()
                        .fill(job.statusColor)
                        .frame(width: 12, height: 12)
                    Text(job.status.uppercased())
                        .font(.title2.bold())
                        .foregroundColor(job.statusColor)
                    Spacer()
                    Text(job.relativeTime)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 4)

                Divider()

                // Transcript
                VStack(alignment: .leading, spacing: 8) {
                    Text("Transcript")
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)

                    if job.transcript.isEmpty {
                        Text("No transcript captured.")
                            .font(.callout)
                            .foregroundStyle(.tertiary)
                            .italic()
                    } else {
                        Text(job.transcript)
                            .font(.callout)
                            .textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationSubtitle(job.name)
    }
}
