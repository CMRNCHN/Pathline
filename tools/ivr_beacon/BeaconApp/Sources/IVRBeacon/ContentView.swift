import SwiftUI

// ── Root view ─────────────────────────────────────────────────────────────────

struct ContentView: View {
    @StateObject private var store = JobStore()
    @State private var selectedID: String?

    var body: some View {
        HSplitView {
            jobList
            detailPanel
        }
        .frame(minWidth: 640, minHeight: 420)
        .toolbar {
            ToolbarItem {
                Button {
                    store.reload()
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .help("Reload results from disk")
            }
        }
    }

    // ── Left: job list ────────────────────────────────────────────────────────

    private var jobList: some View {
        List(store.jobs, selection: $selectedID) { job in
            JobRow(job: job)
                .tag(job.id)
        }
        .listStyle(.sidebar)
        .frame(minWidth: 200, idealWidth: 220, maxWidth: 260)
        .overlay {
            if store.jobs.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                        .font(.largeTitle)
                        .foregroundStyle(.tertiary)
                    Text("No results yet")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                    Text("~/ivr/results/")
                        .font(.caption.monospaced())
                        .foregroundStyle(.tertiary)
                }
            }
        }
    }

    // ── Right: detail panel ───────────────────────────────────────────────────

    @ViewBuilder
    private var detailPanel: some View {
        if let id = selectedID, let job = store.jobs.first(where: { $0.id == id }) {
            DetailPanel(job: job)
                .frame(minWidth: 380, maxWidth: .infinity, maxHeight: .infinity)
        } else {
            Text("Select a job")
                .font(.callout)
                .foregroundStyle(.secondary)
                .frame(minWidth: 380, maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

// ── Job row ───────────────────────────────────────────────────────────────────

struct JobRow: View {
    let job: JobResult

    var body: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(job.statusColor)
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(job.name)
                    .font(.body)
                Text(job.relativeTime)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 3)
    }
}

// ── Detail panel ──────────────────────────────────────────────────────────────

struct DetailPanel: View {
    let job: JobResult
    @State private var transcriptExpanded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {

                // Status badge
                HStack(spacing: 10) {
                    Circle()
                        .fill(job.statusColor)
                        .frame(width: 14, height: 14)
                    Text(job.status.uppercased())
                        .font(.title2.bold())
                        .foregroundColor(job.statusColor)
                }

                Divider()

                // Metadata grid
                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 8) {
                    GridRow {
                        Text("Job").foregroundStyle(.secondary)
                        Text(job.name).fontWeight(.medium)
                    }
                    GridRow {
                        Text("Last run").foregroundStyle(.secondary)
                        Text(job.relativeTime)
                    }
                    GridRow {
                        Text("Timestamp").foregroundStyle(.secondary)
                        Text(job.timestamp)
                            .font(.caption.monospaced())
                    }
                }
                .font(.callout)

                Divider()

                // Transcript disclosure
                DisclosureGroup(
                    isExpanded: $transcriptExpanded,
                    content: {
                        Group {
                            if job.transcript.isEmpty {
                                Text("(no transcript captured)")
                                    .foregroundStyle(.tertiary)
                                    .italic()
                            } else {
                                Text(job.transcript)
                                    .textSelection(.enabled)
                            }
                        }
                        .font(.body.monospaced())
                        .padding(.top, 6)
                        .padding(.leading, 2)
                    },
                    label: {
                        Text("Transcript")
                            .font(.callout.bold())
                    }
                )
            }
            .padding(28)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
