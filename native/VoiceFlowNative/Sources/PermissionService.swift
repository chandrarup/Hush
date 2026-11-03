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
        let inputMonitoringGranted = preflightInputMonitoringPermission()
        return .init(microphone: micGranted, accessibility: accessibilityGranted, inputMonitoring: inputMonitoringGranted)
    }

    func requestMicrophoneAccess() async -> Bool {
        await AVCaptureDevice.requestAccess(for: .audio)
    }

    func openPrivacyPane(_ key: String) {
        let settingsMap: [String: String] = [
            "microphone": "x-apple.systemsettings:com.apple.preference.security?Privacy_Microphone",
            "accessibility": "x-apple.systemsettings:com.apple.preference.security?Privacy_Accessibility",
            "input": "x-apple.systemsettings:com.apple.preference.security?Privacy_ListenEvent"
        ]
        let preferencesMap: [String: String] = [
            "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            "input": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
        ]

        if let urlString = settingsMap[key], let url = URL(string: urlString), NSWorkspace.shared.open(url) {
            return
        }
        if let fallback = preferencesMap[key], let url = URL(string: fallback) {
            _ = NSWorkspace.shared.open(url)
        }
    }

    private func preflightInputMonitoringPermission() -> Bool {
        CGPreflightListenEventAccess()
    }
}
