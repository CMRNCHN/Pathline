import SwiftUI

/// Card representation of a job in the menu bar dropdown.
/// Single click → expand inline transcript.
/// Double click → open Pulse Window.
/// Hover → shadow lift only, no state change.
struct JobCard: View {
    let job: JobResult
    let isExpanded: Bool
    let isRunning: Bool
    let onTap: () -> Void
    let onOpenWindow: () -> Void

    @State private var shadowElevated = false

    private var pulseMode: PulseMode { .from(status: job.status, isRunning: isRunning) }
    private var pulseColor: Color { job.enabled ? job.statusColor : .gray.opacity(0.4) }

    var body: some View {
        VStack(spacing: 0) {
            cardFace
            if isExpanded {
                expandedDetail
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 7)
                .fill(Color(NSColor.controlBackgroundColor))
                .shadow(color: .black.opacity(shadowElevated ? 0.10 : 0.05),
                        radius: shadowElevated ? 5 : 3, y: 1)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 7)
                .strokeBorder(Color.primary.opacity(0.06), lineWidth: 0.5)
        )
        .onHover { shadowElevated = $0 }
        .onTapGesture(count: 2) { onOpenWindow() }
        .onTapGesture(count: 1) { onTap() }
        .animation(.easeInOut(duration: 0.12), value: shadowElevated)
    }

    // ── Card face ─────────────────────────────────────────────────────────────

    private var cardFace: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(pulseColor)
                .frame(width: 7, height: 7)

            VStack(alignment: .leading, spacing: 1) {
                Text(job.name)
                    .font(.system(size: 12, weight: .medium))
                    .lineLimit(1)
                    .foregroundStyle(job.enabled ? .primary : .secondary)

                Text(statusLabel)
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }

            Spacer()

            EKGView(mode: pulseMode, color: pulseColor, cycleWidth: 70)
                .frame(width: 72, height: 18)
                .clipShape(RoundedRectangle(cornerRadius: 3))
                .opacity(job.enabled ? 1 : 0.35)

            Text(job.relativeTime)
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
                .frame(minWidth: 28, alignment: .trailing)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
    }

    // ── Expanded inline transcript ────────────────────────────────────────────

    private var expandedDetail: some View {
        VStack(alignment: .leading, spacing: 6) {
            Divider().padding(.horizontal, 10)

            if job.transcript.isEmpty {
                Text("No transcript captured")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                    .italic()
                    .padding(.horizontal, 10)
            } else {
                ScrollView(.vertical, showsIndicators: false) {
                    Text(job.transcript)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.horizontal, 10)
                }
                .frame(maxHeight: 80)
            }
        }
        .padding(.bottom, 8)
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private var statusLabel: String {
        if isRunning { return "Running now" }
        if !job.enabled { return "Disabled" }
        return job.status.capitalized
    }
}
