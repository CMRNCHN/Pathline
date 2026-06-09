import SwiftUI

struct JobMenuRow: View {
    let job: JobResult
    let isExpanded: Bool
    let onTap: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            compactRow
            if isExpanded {
                expandedDetail
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    // ── Compact row ───────────────────────────────────────────────────────────

    private var compactRow: some View {
        Button(action: onTap) {
            HStack(spacing: 10) {
                Circle()
                    .fill(job.statusColor)
                    .frame(width: 8, height: 8)

                Text(job.name)
                    .font(.callout)
                    .lineLimit(1)

                Spacer()

                Text(job.relativeTime)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Image(systemName: "chevron.right")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(.tertiary)
                    .rotationEffect(.degrees(isExpanded ? 90 : 0))
                    .animation(.easeInOut(duration: 0.15), value: isExpanded)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    // ── Expanded profile ──────────────────────────────────────────────────────

    private var expandedDetail: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                // Status badge
                HStack(spacing: 5) {
                    Circle()
                        .fill(job.statusColor)
                        .frame(width: 6, height: 6)
                    Text(job.status.uppercased())
                        .font(.caption.bold())
                        .foregroundColor(job.statusColor)
                }

                Spacer()

                // Timestamp
                Text(job.relativeTime)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }

            // Transcript or decode failure reason
            if let reason = job.decodeError {
                Text(reason)
                    .font(.caption.monospaced())
                    .foregroundStyle(.purple)
                    .lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
            } else if !job.transcript.isEmpty {
                Text(job.transcript)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("No transcript captured")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .italic()
            }
        }
        .padding(.horizontal, 14)
        .padding(.bottom, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.primary.opacity(0.04))
    }
}
