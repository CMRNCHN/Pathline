import Foundation

/// All write operations on jobs.json and the results directory.
/// Writes to disk only — never touches JobStore. JobWatcher picks up changes.
final class JobService: ObservableObject {
    private let ivrDir = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("ivr")
    private var jobsFile: URL { ivrDir.appendingPathComponent("jobs.json") }
    private var resultsDir: URL { ivrDir.appendingPathComponent("results") }

    func loadConfigs() -> [JobConfig] {
        guard
            let data = try? Data(contentsOf: jobsFile),
            let configs = try? JSONDecoder().decode([JobConfig].self, from: data)
        else { return [] }
        return configs
    }

    func addJob(name: String, cardNumber: String, enabled: Bool) throws {
        var configs = loadConfigs()
        guard !configs.contains(where: { $0.name == name }) else {
            throw CocoaError(.fileWriteFileExists,
                userInfo: [NSLocalizedDescriptionKey: "A job named '\(name)' already exists."])
        }
        configs.append(JobConfig(name: name, card_number: cardNumber, enabled: enabled))
        try save(configs)
    }

    func toggleEnabled(name: String) throws {
        var configs = loadConfigs()
        guard let idx = configs.firstIndex(where: { $0.name == name }) else { return }
        configs[idx].enabled.toggle()
        try save(configs)
    }

    func deleteJob(name: String) throws {
        var configs = loadConfigs()
        configs.removeAll { $0.name == name }
        try save(configs)
        let dir = resultsDir.appendingPathComponent(name)
        try? FileManager.default.removeItem(at: dir)
    }

    private func save(_ configs: [JobConfig]) throws {
        try FileManager.default.createDirectory(at: ivrDir, withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(configs).write(to: jobsFile, options: .atomic)
    }
}
