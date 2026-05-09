import Foundation
import AppKit

@MainActor
final class AppCoordinator: ObservableObject {
    @Published var state: PipelineState = .idle
    @Published var statusText = "Ready"
    @Published var latestOutput: PipelineOutput?
    @Published var config: VoiceFlowConfig

    private let configStore = ConfigStore()
    private let historyStore = HistoryStore()
    private let migrationImporter = MigrationImporter()
    private let permissionService = PermissionService()
    private let notificationService = NotificationService()
    private let textInjector: TextInjecting = PasteboardTextInjector()
    private let pipeline: TranscriptionPipeline = NativeTranscriptionPipeline()

    init() {
        self.config = configStore.load()
    }

    func start() {
        migrationImporter.importIfNeeded(configStore: configStore, historyStore: historyStore)
        config = configStore.load()
        statusText = permissionService.currentStatus().allGranted ? "Ready" : "Permissions required"
    }

    func saveConfig() {
        try? configStore.save(config)
    }

    func startRecording() {
        guard state == .idle else { return }
        do {
            try pipeline.startRecording()
            state = .recording
            statusText = "Recording..."
        } catch {
            state = .failed
            statusText = "Failed to start recording"
        }
    }

    func stopAndProcess() {
        guard state == .recording else { return }
        state = .processing
        statusText = "Processing..."

        Task {
            do {
                let output = try await pipeline.stopRecordingAndTranscribe()
                latestOutput = output
                let saveID = historyStore.save(raw: output.rawText, clean: output.cleanText, level: config.cleanupLevel, app: NSWorkspace.shared.frontmostApplication?.localizedName)
                let injected = textInjector.inject(output.cleanText)
                notificationService.sendResult(raw: output.rawText, clean: output.cleanText)
                state = .idle
                if saveID < 0 {
                    statusText = "Save failed; check logs"
                } else if !injected {
                    statusText = "Inject failed; check Accessibility"
                } else {
                    statusText = "Ready"
                }
            } catch {
                state = .failed
                statusText = "Pipeline failed"
            }
        }
    }

    func history() -> [HistoryEntry] {
        historyStore.fetch(limit: 200)
    }

    func openSystemSettingsForPermission(_ key: String) {
        permissionService.openPrivacyPane(key)
    }
}
