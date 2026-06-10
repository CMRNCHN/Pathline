import SwiftUI

struct PulseMenuView: View {
    @EnvironmentObject var store: JobStore
    @EnvironmentObject var service: JobService
    @Environment(\.openWindow) private var openWindow

    @State private var expandedJobID: String?
    @State private var showingAddForm = false

    var body: some View {
        let ranked = PulseMenuModel.rankedJobs(from: store.jobs)
        let (visible, overflow) = PulseMenuModel.visibleJobs(ranked)
        let snap = PulseMenuModel.Snapshot(
            visible: visible,
            overflowCount: overflow,
            metrics: PulseMenuModel.metrics(from: ranked)
        )

        VStack(spacing: 0) {
            header(metrics: snap.metrics, pulseMode: globalPulseMode(ranked: ranked))
            if showingAddForm {
                Divider()
                AddJobForm(onDismiss: { showingAddForm = false }, service: service)
            } else if snap.visible.isEmpty {
                emptyState
            } else {
                Divider()
                cardList(snap: snap)
            }
            Divider()
            footer
        }
        .background(Color(NSColor.windowBackgroundColor))
    }

    // ── Header ────────────────────────────────────────────────────────────────

    private func header(metrics: JobMetrics, pulseMode: PulseMode) -> some View {
        HStack(spacing: 10) {
            Text("Pathline Pulse")
                .font(.system(size: 13, weight: .semibold))

            Spacer()

            if metrics.hasAttention {
                Text("⚠ \(metrics.attentionCount)")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(.red)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 2)
                    .background(.red.opacity(0.10), in: Capsule())
            }

            EKGView(mode: pulseMode, cycleWidth: 80)
                .frame(width: 80, height: 24)
                .clipShape(RoundedRectangle(cornerRadius: 4))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
    }

    private func globalPulseMode(ranked: [JobResult]) -> PulseMode {
        if store.isRunning { return .running }
        let statuses = ranked.map { $0.status.uppercased() }
        if statuses.contains("RED")                              { return .error }
        if statuses.contains("ORANGE") || statuses.contains("YELLOW") { return .warning }
        if !ranked.isEmpty                                       { return .healthy }
        return .unknown
    }

    // ── Card list ─────────────────────────────────────────────────────────────

    private func cardList(snap: PulseMenuModel.Snapshot) -> some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 5) {
                ForEach(snap.visible) { job in
                    cardView(for: job)
                }
                if snap.overflowCount > 0 {
                    Text("\(snap.overflowCount) more · Open Pulse for full view")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 4)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
        }
        .frame(maxHeight: 380)
    }

    @ViewBuilder
    private func cardView(for job: JobResult) -> some View {
        JobCard(
            job: job,
            isExpanded: expandedJobID == job.id,
            isRunning: store.isRunning,
            onTap: {
                let id = job.id
                withAnimation(.easeInOut(duration: 0.15)) {
                    expandedJobID = expandedJobID == id ? nil : id
                }
            },
            onOpenWindow: {
                openWindow(id: "pulse-window")
                NSApp.sendAction(#selector(NSPopover.performClose(_:)), to: nil, from: nil)
            }
        )
    }

    // ── Empty state ───────────────────────────────────────────────────────────

    private var emptyState: some View {
        VStack(spacing: 8) {
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
        .padding(.vertical, 28)
    }

    // ── Footer ────────────────────────────────────────────────────────────────

    private var footer: some View {
        HStack(spacing: 6) {
            Button {
                withAnimation(.easeInOut(duration: 0.15)) {
                    showingAddForm.toggle()
                    expandedJobID = nil
                }
            } label: {
                Text(showingAddForm ? "Cancel" : "+ New Suite")
                    .font(.system(size: 11))
            }
            .buttonStyle(.borderless)
            .foregroundStyle(.secondary)

            Spacer()

            Button("Open Pulse") {
                openWindow(id: "pulse-window")
                NSApp.sendAction(#selector(NSPopover.performClose(_:)), to: nil, from: nil)
            }
            .buttonStyle(.borderless)
            .font(.system(size: 11))

            Text("·").foregroundStyle(.tertiary).font(.caption)

            Button("Open Pathline") { openPathlineApp() }
                .buttonStyle(.borderless)
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private func openPathlineApp() {
        let candidates = ["/Applications/Pathline.app",
                          "\(NSHomeDirectory())/Applications/Pathline.app"]
        for path in candidates where FileManager.default.fileExists(atPath: path) {
            NSWorkspace.shared.openApplication(at: URL(fileURLWithPath: path),
                                               configuration: .init())
            return
        }
        NSWorkspace.shared.open(URL(string: "https://pathline.app")!)
    }
}

// ── Add job form ──────────────────────────────────────────────────────────────

private struct AddJobForm: View {
    let onDismiss: () -> Void
    let service: JobService
    @State private var jobName = ""
    @State private var cardNumber = ""
    @State private var enabled = true
    @State private var error: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("New Job")
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            TextField("Job name", text: $jobName).textFieldStyle(.roundedBorder).font(.callout)
            SecureField("Card number", text: $cardNumber).textFieldStyle(.roundedBorder).font(.callout)
            Toggle("Enabled", isOn: $enabled).font(.callout)
            if let err = error { Text(err).font(.caption).foregroundColor(.red) }
            HStack {
                Button("Cancel", action: onDismiss).buttonStyle(.borderless).foregroundStyle(.secondary)
                Spacer()
                Button("Add") { submit() }
                    .buttonStyle(.borderedProminent).controlSize(.small)
                    .disabled(jobName.trimmingCharacters(in: .whitespaces).isEmpty || cardNumber.isEmpty)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
    }

    private func submit() {
        let name = jobName.trimmingCharacters(in: .whitespaces)
        do {
            try service.addJob(name: name, cardNumber: cardNumber, enabled: enabled)
            onDismiss()
        } catch { self.error = error.localizedDescription }
    }
}
