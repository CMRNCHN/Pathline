import Foundation
import SwiftUI

// ── Data model ────────────────────────────────────────────────────────────────

struct JobResult: Identifiable, Equatable {
    var id: String { name }
    let name: String
    let status: String
    let transcript: String
    let timestamp: String
    let decodeError: String?      // non-nil → file was found but could not be decoded

    var statusColor: Color {
        if decodeError != nil { return .purple }
        switch status.uppercased() {
        case "GREEN":  return .green
        case "ORANGE": return .orange
        case "YELLOW": return .yellow
        case "RED":    return .red
        default:       return .gray
        }
    }

    var relativeTime: String {
        guard decodeError == nil else { return "—" }
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

private enum DecodeOutcome {
    case success(JobResult)
    case missing
    case corrupted(String)
}

private func readResult(at url: URL, name: String) -> DecodeOutcome {
    guard let data = try? Data(contentsOf: url) else {
        return .missing
    }
    do {
        let file = try JSONDecoder().decode(ResultFile.self, from: data)
        return .success(JobResult(name: name, status: file.status, transcript: file.transcript,
                                  timestamp: file.timestamp, decodeError: nil))
    } catch {
        return .corrupted(error.localizedDescription)
    }
}

// ── Jobs config (~/ivr/jobs.json) ────────────────────────────────────────────

private struct JobConfig: Codable {
    var name: String
    var card_number: String
    var enabled: Bool
}

// ── Store ─────────────────────────────────────────────────────────────────────

@MainActor
final class JobStore: ObservableObject {
    @Published var jobs: [JobResult] = []

    private let ivrDir = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("ivr")
    private var resultsDir: URL { ivrDir.appendingPathComponent("results") }
    private var jobsFile: URL { ivrDir.appendingPathComponent("jobs.json") }

    private var timer: Timer?

    init() {
        reload()
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.reload() }
        }
    }

    var malformedCount: Int { jobs.filter { $0.decodeError != nil }.count }

    func reload() {
        let fm = FileManager.default

        // jobs.json is the authoritative job list. Only show results for jobs
        // defined there; orphan result dirs from removed jobs are ignored.
        // Falls back to showing all results when jobs.json is absent/unparseable.
        let knownNames: Set<String>?
        if let data = try? Data(contentsOf: jobsFile),
           let configs = try? JSONDecoder().decode([JobConfig].self, from: data) {
            knownNames = Set(configs.map { $0.name })
        } else {
            knownNames = nil
        }

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
            .filter { knownNames == nil || knownNames!.contains($0.lastPathComponent) }
            .compactMap { dir -> JobResult? in
                let name = dir.lastPathComponent
                switch readResult(at: dir.appendingPathComponent("latest.json"), name: name) {
                case .success(let job):      return job
                case .missing:               return nil
                case .corrupted(let reason): return JobResult(name: name, status: "MALFORMED",
                                                              transcript: "", timestamp: "",
                                                              decodeError: reason)
                }
            }
            .sorted { $0.name < $1.name }
    }

    func addJob(name: String, cardNumber: String, enabled: Bool) throws {
        let fm = FileManager.default
        try fm.createDirectory(at: ivrDir, withIntermediateDirectories: true)

        var configs: [JobConfig] = []
        if let data = try? Data(contentsOf: jobsFile),
           let existing = try? JSONDecoder().decode([JobConfig].self, from: data) {
            configs = existing
        }
        guard !configs.contains(where: { $0.name == name }) else {
            throw CocoaError(.fileWriteFileExists,
                             userInfo: [NSLocalizedDescriptionKey: "A job named '\(name)' already exists."])
        }
        configs.append(JobConfig(name: name, card_number: cardNumber, enabled: enabled))
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(configs)
        try data.write(to: jobsFile, options: .atomic)
        reload()
    }

    deinit { timer?.invalidate() }
}
