import Foundation

/// Severity ranking and degradation logic for job statuses.
/// Owns all "what counts as worse" reasoning — kept out of the model.
enum JobStatusEvaluator {
    /// Higher rank = worse. Unknown/error statuses rank highest.
    static func rank(_ status: String) -> Int {
        switch status.uppercased() {
        case "GREEN":  return 0
        case "YELLOW": return 1
        case "ORANGE": return 2
        case "RED":    return 3
        default:       return 4
        }
    }

    static func isDegradation(from oldStatus: String, to newStatus: String) -> Bool {
        rank(newStatus) > rank(oldStatus)
    }
}
