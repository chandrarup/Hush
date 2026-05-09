import Foundation
import AVFoundation
import ApplicationServices
import AppKit

struct PermissionStatus {
    let microphone: Bool
    let accessibility: Bool
    let inputMonitoring: Bool

    var allGranted: Bool { microphone && accessibility && inputMonitoring }
}

final class PermissionService {
    func currentStatus() -> PermissionStatus {
        let micGranted = AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
        let accessibilityGranted = AXIsProcessTrusted()
        let inputMonitoringGranted = accessibilityGranted
        return .init(microphone: micGranted, accessibility: accessibilityGranted, inputMonitoring: inputMonitoringGranted)
    }

    func requestMicrophoneAccess() async -> Bool {
        await AVCaptureDevice.requestAccess(for: .audio)
    }

    func openPrivacyPane(_ key: String) {
        let map: [String: String] = [
            "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            "input": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
        ]

        guard let urlString = map[key], let url = URL(string: urlString) else { return }
        NSWorkspace.shared.open(url)
    }
}
