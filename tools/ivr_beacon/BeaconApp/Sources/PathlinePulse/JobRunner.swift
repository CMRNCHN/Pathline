import Foundation

/// Executes the batch script. Sets isRunning on the store — nothing else.
/// Results land in ~/ivr/results/; JobWatcher detects and updates state.
@MainActor
final class JobRunner: ObservableObject {
    private let batchScript = URL(fileURLWithPath: NSHomeDirectory())
        .appendingPathComponent("ivr/run_ivr_batch.sh")

    func runAll(store: JobStore) {
        guard !store.isRunning else { return }
        guard FileManager.default.fileExists(atPath: batchScript.path) else {
            print("[JobRunner] batch script not found: \(batchScript.path)")
            return
        }

        store.setRunning(true)

        let scriptPath = batchScript.path
        Task.detached(priority: .background) {
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: "/bin/bash")
            proc.arguments = [scriptPath]

            let pipe = Pipe()
            proc.standardOutput = pipe
            proc.standardError = pipe

            do {
                try proc.run()
                proc.waitUntilExit()
            } catch {
                print("[JobRunner] launch error: \(error)")
            }

            await MainActor.run { store.setRunning(false) }
            // No reload() — JobWatcher sees the new result files automatically.
        }
    }
}
