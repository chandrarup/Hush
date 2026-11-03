import SwiftUI

struct ContentView: View {
    @ObservedObject var coordinator: AppCoordinator

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("VoiceFlow")
                .font(.headline)
            Text(coordinator.statusText)
                .foregroundStyle(.secondary)

            HStack {
                Button("Start") { coordinator.startRecording() }
                    .disabled(coordinator.state != .idle)
                Button("Stop") { coordinator.stopAndProcess() }
                    .disabled(coordinator.state != .recording)
            }

            if let output = coordinator.latestOutput {
                GroupBox("Latest") {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Raw: \(output.rawText)")
                            .lineLimit(3)
                        Text("Clean: \(output.cleanText)")
                            .lineLimit(3)
                    }
                    .font(.caption)
                }
            }

            Divider()

            HStack {
                Button("Microphone") { coordinator.openSystemSettingsForPermission("microphone") }
                Button("Accessibility") { coordinator.openSystemSettingsForPermission("accessibility") }
                Button("Input Monitoring") { coordinator.openSystemSettingsForPermission("input") }
            }
        }
        .padding(14)
        .frame(width: 360)
    }
}
