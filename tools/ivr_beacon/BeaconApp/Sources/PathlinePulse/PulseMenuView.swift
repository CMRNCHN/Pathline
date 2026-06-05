import SwiftUI

struct PulseMenuView: View {
    @EnvironmentObject var store: JobStore
    @Environment(\.openWindow) private var openWindow
    @State private var expandedJobID: String?
    @State private var showingAddForm = false

    // Overall signal color — worst status wins
    private var signalColor: Color {
        let statuses = store.jobs.map { $0.status.uppercased() }
        if statuses.contains("RED")    { return .red }
        if statuses.contains("ORANGE") { return .orange }
        if statuses.contains("YELLOW") { return .yellow }
        if statuses.allSatisfy({ $0 == "GREEN" }) && !statuses.isEmpty { return .green }
        return .gray
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            if showingAddForm {
                AddJobForm(onDismiss: { showingAddForm = false }, store: store)
                Divider()
            } else if store.jobs.isEmpty {
                emptyState
            } else {
                jobList
            }
            Divider()
            footer
        }
    }

    // ── Header ────────────────────────────────────────────────────────────────

    private var header: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Pathline Pulse")
                    .font(.system(size: 13, weight: .semibold))
                Text(store.jobs.isEmpty
                     ? "No jobs configured"
                     : "\(store.jobs.count) job\(store.jobs.count == 1 ? "" : "s")")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            EKGView(color: signalColor)
                .frame(width: 80, height: 26)
                .clipShape(RoundedRectangle(cornerRadius: 4))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }

    // ── Job list ──────────────────────────────────────────────────────────────

    private var jobList: some View {
        ScrollView(.vertical, showsIndicators: false) {
            LazyVStack(spacing: 0) {
                ForEach(store.jobs) { job in
                    JobMenuRow(
                        job: job,
                        isExpanded: expandedJobID == job.id,
                        onTap: {
                            withAnimation(.easeInOut(duration: 0.15)) {
                                expandedJobID = expandedJobID == job.id ? nil : job.id
                            }
                        }
                    )
                    if job.id != store.jobs.last?.id {
                        Divider()
                            .padding(.leading, 32)
                    }
                }
            }
        }
        .frame(maxHeight: 340)
    }

    private var emptyState: some View {
        VStack(spacing: 6) {
            Image(systemName: "waveform.path.ecg")
                .font(.title2)
                .foregroundStyle(.tertiary)
            Text("No results yet")
                .font(.callout)
                .foregroundStyle(.secondary)
            Text("~/ivr/results/")
                .font(.caption.monospaced())
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
    }

    // ── Footer ────────────────────────────────────────────────────────────────

    private var footer: some View {
        HStack(spacing: 6) {
            // Add suite
            Button {
                withAnimation(.easeInOut(duration: 0.15)) {
                    showingAddForm.toggle()
                    expandedJobID = nil
                }
            } label: {
                Image(systemName: showingAddForm ? "xmark.circle" : "plus.circle")
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .help("Add job")

            Spacer()

            Button("Open Pulse") {
                openWindow(id: "pulse-window")
                // Dismiss the popover
                NSApp.sendAction(#selector(NSPopover.performClose(_:)), to: nil, from: nil)
            }
            .buttonStyle(.borderless)
            .font(.callout)

            Text("·")
                .foregroundStyle(.tertiary)
                .font(.caption)

            Button("Open Pathline") {
                openPathlineApp()
            }
            .buttonStyle(.borderless)
            .font(.callout)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private func openPathlineApp() {
        let candidates = [
            "/Applications/Pathline.app",
            "\(NSHomeDirectory())/Applications/Pathline.app",
        ]
        for path in candidates {
            let url = URL(fileURLWithPath: path)
            if FileManager.default.fileExists(atPath: path) {
                NSWorkspace.shared.openApplication(
                    at: url,
                    configuration: NSWorkspace.OpenConfiguration()
                )
                return
            }
        }
        // App not found — open the Pathline web app as fallback
        if let url = URL(string: "https://pathline.app") {
            NSWorkspace.shared.open(url)
        }
    }
}

// ── Inline add-job form ───────────────────────────────────────────────────────

private struct AddJobForm: View {
    let onDismiss: () -> Void
    let store: JobStore

    @State private var jobName = ""
    @State private var cardNumber = ""
    @State private var enabled = true
    @State private var error: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("New Job")
                .font(.caption.bold())
                .foregroundStyle(.secondary)

            TextField("Job name (e.g. job_c)", text: $jobName)
                .textFieldStyle(.roundedBorder)
                .font(.callout)

            SecureField("Card number", text: $cardNumber)
                .textFieldStyle(.roundedBorder)
                .font(.callout)

            Toggle("Enabled", isOn: $enabled)
                .font(.callout)

            if let err = error {
                Text(err)
                    .font(.caption)
                    .foregroundColor(.red)
            }

            HStack {
                Button("Cancel", action: onDismiss)
                    .buttonStyle(.borderless)
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Add") { submit() }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(jobName.trimmingCharacters(in: .whitespaces).isEmpty || cardNumber.isEmpty)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }

    private func submit() {
        let name = jobName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty, !cardNumber.isEmpty else { return }
        do {
            try store.addJob(name: name, cardNumber: cardNumber, enabled: enabled)
            onDismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
