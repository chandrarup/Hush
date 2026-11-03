import SwiftUI

@main
struct VoiceFlowNativeApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        MenuBarExtra("VoiceFlow", systemImage: "mic") {
            ContentView(coordinator: appDelegate.coordinator)
        }
        .menuBarExtraStyle(.window)

        Settings {
            SettingsView(coordinator: appDelegate.coordinator)
        }
    }
}
