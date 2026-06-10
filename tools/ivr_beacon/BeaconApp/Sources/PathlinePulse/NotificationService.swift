import Foundation
import UserNotifications

/// Owns notification permission lifecycle and delivery. No state, no UI.
final class NotificationService {
    private static let permissionRequestedKey = "notificationPermissionRequested"

    func requestPermissionIfNeeded() {
        guard !UserDefaults.standard.bool(forKey: Self.permissionRequestedKey) else { return }
        UserDefaults.standard.set(true, forKey: Self.permissionRequestedKey)
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    func notify(job: JobResult, degradedFrom oldStatus: String) {
        let content = UNMutableNotificationContent()
        content.title = "Pathline Pulse — \(job.status.uppercased())"
        content.body = "\(job.name): \(oldStatus.uppercased()) → \(job.status.uppercased())"
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "pulse.\(job.name).\(job.timestamp)",
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(request) { _ in }
    }
}
