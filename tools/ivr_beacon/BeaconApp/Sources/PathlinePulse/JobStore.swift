import Foundation

/// Passive state holder.
///
/// Read surface: @Published vars — any code may observe.
/// Write surface: update(jobs:) and setRunning(_:) — called only by JobWatcher and JobRunner.
/// Views must never write to this store. Private(set) enforces that at the call site.
@MainActor
final class JobStore: ObservableObject {
    @Published private(set) var jobs: [JobResult] = []
    @Published private(set) var isRunning = false

    private let notifications: NotificationService

    init(notifications: NotificationService) {
        self.notifications = notifications
    }

    /// Called only by JobWatcher. Diffs state and fires degradation notifications.
    func update(jobs newJobs: [JobResult]) {
        let oldByName = Dictionary(uniqueKeysWithValues: jobs.map { ($0.name, $0) })
        for job in newJobs {
            if let old = oldByName[job.name],
               JobStatusEvaluator.isDegradation(from: old.status, to: job.status) {
                notifications.notify(job: job, degradedFrom: old.status)
            }
        }
        jobs = newJobs
    }

    /// Called only by JobRunner. Explicit write method — not a settable property.
    func setRunning(_ value: Bool) {
        isRunning = value
    }
}
