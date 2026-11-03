import Foundation
import UserNotifications

final class NotificationService {
    func sendResult(raw: String, clean: String) {
        let content = UNMutableNotificationContent()
        content.title = "VoiceFlow"
        content.body = "Raw: \(truncate(raw))\nClean: \(truncate(clean))"

        let req = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(req)
    }

    private func truncate(_ text: String, maxCharacters: Int = 60) -> String {
        guard text.count > maxCharacters else { return text }
        return String(text.prefix(maxCharacters)) + "…"
    }
}
