import SwiftUI

/// Shared context menu for job rows in both the menu bar and full window.
/// Single source of truth for enable/disable/delete actions.
struct JobContextMenu: ViewModifier {
    let job: JobResult
    let service: JobService
    var onDeleted: (() -> Void)? = nil

    func body(content: Content) -> some View {
        content.contextMenu {
            Button {
                try? service.toggleEnabled(name: job.name)
            } label: {
                Label(
                    job.enabled ? "Disable Job" : "Enable Job",
                    systemImage: job.enabled ? "pause.circle" : "play.circle"
                )
            }

            Divider()

            Button(role: .destructive) {
                onDeleted?()
                try? service.deleteJob(name: job.name)
            } label: {
                Label("Delete Job", systemImage: "trash")
            }
        }
    }
}

extension View {
    func jobContextMenu(_ job: JobResult, service: JobService, onDeleted: (() -> Void)? = nil) -> some View {
        modifier(JobContextMenu(job: job, service: service, onDeleted: onDeleted))
    }
}
