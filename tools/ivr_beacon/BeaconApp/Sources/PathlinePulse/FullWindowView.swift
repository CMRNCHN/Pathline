import SwiftUI

struct FullWindowView: View {
    @EnvironmentObject var store: JobStore
    @EnvironmentObject var runner: JobRunner
    @EnvironmentObject var service: JobService
    @State private var selectedJobID: String?

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            if let id = selectedJobID, let job = store.jobs.first(where: { $0.id == id }) {
                JobDetailView(job: job, service: service)
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
                    runner.runAll(store: store)
                } label: {
                    if store.isRunning {
                        ProgressView().scaleEffect(0.7)
                    } else {
                        Image(systemName: "play.circle")
                    }
                }
                .disabled(store.isRunning)
                .help(store.isRunning ? "Running…" : "Run all jobs now")
            }
        }
    }

    private var sidebar: some View {
        List(store.jobs, selection: $selectedJobID) { job in
            sidebarRow(for: job)
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

    @ViewBuilder
    private func sidebarRow(for job: JobResult) -> some View {
        HStack(spacing: 10) {
            Circle()
                .fill(job.enabled ? job.statusColor : Color.gray.opacity(0.5))
                .frame(width: 9, height: 9)
            VStack(alignment: .leading, spacing: 2) {
                Text(job.name)
                    .font(.callout)
                    .foregroundStyle(job.enabled ? .primary : .secondary)
                Text(job.relativeTime)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .tag(job.id)
        .padding(.vertical, 3)
        .jobContextMenu(job, service: service, onDeleted: {
            if selectedJobID == job.id { selectedJobID = nil }
        })
    }
}

// ── Job detail panel ──────────────────────────────────────────────────────────

private struct JobDetailView: View {
    let job: JobResult
    let service: JobService

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack(spacing: 10) {
                    Circle()
                        .fill(job.enabled ? job.statusColor : Color.gray.opacity(0.5))
                        .frame(width: 12, height: 12)
                    Text(job.enabled ? job.status.uppercased() : "DISABLED")
                        .font(.title2.bold())
                        .foregroundColor(job.enabled ? job.statusColor : .secondary)
                    Spacer()
                    Text(job.relativeTime)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 4)

                Divider()

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
