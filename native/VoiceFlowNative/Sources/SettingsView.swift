import SwiftUI

struct SettingsView: View {
    @ObservedObject var coordinator: AppCoordinator

    var body: some View {
        Form {
            TextField("Hotkey", text: $coordinator.config.hotkey)
            TextField("ASR Engine", text: $coordinator.config.asrEngine)
            TextField("ASR Model", text: $coordinator.config.asrModel)
            TextField("Cleanup Level", text: $coordinator.config.cleanupLevel)
            TextField("Ollama Model", text: $coordinator.config.ollamaModel)
            TextField("Ollama Base URL", text: $coordinator.config.ollamaBaseURL)
            TextField("Docker LLM URL", text: $coordinator.config.dockerLLMURL)

            Button("Save") {
                coordinator.saveConfig()
            }
        }
        .padding()
        .frame(width: 520)
    }
}
