import Foundation
import SwiftUI

// ── Data models — pure value types, no logic ──────────────────────────────────

struct JobResult: Identifiable, Equatable {
    var id: String { name }
    let name: String
    let status: String
    let transcript: String
    let timestamp: String
    let enabled: Bool

    var statusColor: Color {
        switch status.uppercased() {
        case "GREEN":  return .green
        case "ORANGE": return .orange
        case "YELLOW": return .yellow
        case "RED":    return .red
        default:       return .gray
        }
    }

    var relativeTime: String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = iso.date(from: timestamp) ?? ISO8601DateFormatter().date(from: timestamp) else {
            return timestamp
        }
        let fmt = RelativeDateTimeFormatter()
        fmt.unitsStyle = .abbreviated
        return fmt.localizedString(for: date, relativeTo: Date())
    }
}

struct JobConfig: Codable {
    var name: String
    var card_number: String
    var enabled: Bool
}
