import Foundation
import SwiftUI

// ── Data model ────────────────────────────────────────────────────────────────

struct JobResult: Identifiable, Equatable {
    var id: String { name }
    let name: String
    let status: String
    let transcript: String
    let timestamp: String

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
        let iso2 = ISO8601DateFormatter()
        guard let date = iso.date(from: timestamp) ?? iso2.date(from: timestamp) else {
            return timestamp
        }
        let fmt = RelativeDateTimeFormatter()
        fmt.unitsStyle = .abbreviated
        return fmt.localizedString(for: date, relativeTo: Date())
    }
}

// ── File reader ───────────────────────────────────────────────────────────────

private struct ResultFile: Decodable {
    let status: String
    let transcript: String
    let timestamp: String
}

private func readResult(at url: URL) -> JobResult? {
    guard
        let data = try? Data(contentsOf: url),
        let file = try? JSONDecoder().decode(ResultFile.self, from: data)
    else { return nil }
    let name = url.deletingLastPathComponent().lastPathComponent
    return JobResult(
        name: name,
        status: file.status,
        transcript: file.transcript,
        timestamp: file.timestamp
    )
}

// ── Store ─────────────────────────────────────────────────────────────────────

@MainActor
final class JobStore: ObservableObject {
    @Published var jobs: [JobResult] = []

    private let resultsDir = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent("ivr/results")

    private var timer: Timer?

    init() {
        reload()
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.reload() }
        }
    }

    func reload() {
        let fm = FileManager.default
        guard
            fm.fileExists(atPath: resultsDir.path),
            let dirs = try? fm.contentsOfDirectory(
                at: resultsDir,
                includingPropertiesForKeys: [.isDirectoryKey],
                options: .skipsHiddenFiles
            )
        else {
            jobs = []
            return
        }
        jobs = dirs
            .compactMap { dir in readResult(at: dir.appendingPathComponent("latest.json")) }
            .sorted { $0.name < $1.name }
    }

    deinit { timer?.invalidate() }
}
