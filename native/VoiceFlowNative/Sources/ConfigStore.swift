import Foundation

final class ConfigStore {
    private let fm = FileManager.default

    private var appSupportDirectory: URL {
        let base = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support", isDirectory: true)
        return base.appendingPathComponent("VoiceFlow", isDirectory: true)
    }

    private var configURL: URL {
        appSupportDirectory.appendingPathComponent("config.json")
    }

    func load() -> VoiceFlowConfig {
        do {
            let data = try Data(contentsOf: configURL)
            return try JSONDecoder().decode(VoiceFlowConfig.self, from: data)
        } catch {
            return VoiceFlowConfig()
        }
    }

    func save(_ config: VoiceFlowConfig) throws {
        try fm.createDirectory(at: appSupportDirectory, withIntermediateDirectories: true)
        let data = try JSONEncoder().encode(config)
        try data.write(to: configURL, options: .atomic)
    }
}
