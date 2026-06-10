import Foundation

/// Data-layer rules for the menu bar dropdown.
/// Three public pure transforms. snapshot() is private orchestration — callers use the steps directly.
enum PulseMenuModel {
    static let visibleLimit = 6

    // ── Step 1a — active set (inclusion policy) ───────────────────────────────
    /// Jobs that are part of the runtime workload. Filtering only — no ordering.
    static func activeJobs(from jobs: [JobResult]) -> [JobResult] {
        jobs.filter { $0.enabled }
    }

    // ── Step 1b — rank (ordering policy) ──────────────────────────────────────
    /// Severity-ordered active jobs. Sorting only — no filtering.
    static func rankedJobs(from jobs: [JobResult]) -> [JobResult] {
        activeJobs(from: jobs)
            .sorted { JobStatusEvaluator.rank($0.status) > JobStatusEvaluator.rank($1.status) }
    }

    // ── Step 2 — cap ──────────────────────────────────────────────────────────
    /// Slices ranked list to visible window. Returns (visible, overflowCount).
    static func visibleJobs(_ ranked: [JobResult], limit: Int = visibleLimit) -> (visible: [JobResult], overflow: Int) {
        (Array(ranked.prefix(limit)), max(0, ranked.count - limit))
    }

    // ── Step 3 — metrics ──────────────────────────────────────────────────────
    /// Pure data metrics from a ranked list. No UI formatting — callers render.
    static func metrics(from ranked: [JobResult]) -> JobMetrics {
        let attentionCount = ranked.filter {
            ["RED", "ORANGE"].contains($0.status.uppercased())
        }.count
        return JobMetrics(attentionCount: attentionCount)
    }

    struct Snapshot {
        let visible: [JobResult]
        let overflowCount: Int
        let metrics: JobMetrics
    }
}

/// Pure data. No UI strings, no formatting hints.
struct JobMetrics {
    let attentionCount: Int
    var hasAttention: Bool { attentionCount > 0 }
}
