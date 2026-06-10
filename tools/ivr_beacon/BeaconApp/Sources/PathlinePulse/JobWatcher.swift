import Foundation

/// The only source of truth for state refresh.
/// Watches both ~/ivr/ (jobs.json changes) and ~/ivr/results/ (new results).
/// On any filesystem event, reads files and calls store.update(jobs:).
final class JobWatcher {
    private let ivrDir: URL
    private var resultsDir: URL { ivrDir.appendingPathComponent("results") }
    private var jobsFile: URL { ivrDir.appendingPathComponent("jobs.json") }

    private let store: JobStore
    private var sources: [DispatchSourceFileSystemObject] = []

    init(store: JobStore) {
        self.store = store
        self.ivrDir = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("ivr")
        ensureDirectories()
        startWatching()
        // Initial load
        Task { @MainActor in self.reload() }
    }

    // MARK: – File watching

    private func ensureDirectories() {
        let fm = FileManager.default
        try? fm.createDirectory(at: resultsDir, withIntermediateDirectories: true)
    }

    private func startWatching() {
        watch(url: ivrDir)
        watch(url: resultsDir)
    }

    private func watch(url: URL) {
        let fd = open(url.path, O_EVTONLY)
        guard fd >= 0 else { return }

        let source = DispatchSource.makeFileSystemObjectSource(
            fileDescriptor: fd,
            eventMask: [.write, .rename, .delete],
            queue: .main
        )
        source.setEventHandler { [weak self] in
            self?.reload()
        }
        source.setCancelHandler { close(fd) }
        source.resume()
        sources.append(source)
    }

    // MARK: – Read + build snapshot

    private func reload() {
        let enabledByName = readConfigs().reduce(into: [String: Bool]()) {
            $0[$1.name] = $1.enabled
        }

        let fm = FileManager.default
        guard
            fm.fileExists(atPath: resultsDir.path),
            let dirs = try? fm.contentsOfDirectory(
                at: resultsDir,
                includingPropertiesForKeys: [.isDirectoryKey],
                options: .skipsHiddenFiles
            )
        else {
            Task { @MainActor in self.store.update(jobs: []) }
            return
        }

        let jobs = dirs
            .compactMap { dir -> JobResult? in
                readResult(at: dir.appendingPathComponent("latest.json"),
                           enabled: enabledByName[dir.lastPathComponent] ?? true)
            }
            .sorted { $0.name < $1.name }

        Task { @MainActor in self.store.update(jobs: jobs) }
    }

    // MARK: – File readers

    private struct ResultFile: Decodable {
        let status: String
        let transcript: String
        let timestamp: String
    }

    private func readResult(at url: URL, enabled: Bool) -> JobResult? {
        guard
            let data = try? Data(contentsOf: url),
            let file = try? JSONDecoder().decode(ResultFile.self, from: data)
        else { return nil }
        return JobResult(
            name: url.deletingLastPathComponent().lastPathComponent,
            status: file.status,
            transcript: file.transcript,
            timestamp: file.timestamp,
            enabled: enabled
        )
    }

    private func readConfigs() -> [JobConfig] {
        guard
            let data = try? Data(contentsOf: jobsFile),
            let configs = try? JSONDecoder().decode([JobConfig].self, from: data)
        else { return [] }
        return configs
    }

    deinit {
        sources.forEach { $0.cancel() }
    }
}
