import Foundation
import SQLite3

final class MigrationImporter {
    private let legacyDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".voiceflow", isDirectory: true)
    private let markerURL: URL

    init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support", isDirectory: true)
        let appSupport = base.appendingPathComponent("VoiceFlow", isDirectory: true)
        try? FileManager.default.createDirectory(at: appSupport, withIntermediateDirectories: true)
        self.markerURL = appSupport.appendingPathComponent("migration_v1_complete")
    }

    func importIfNeeded(configStore: ConfigStore, historyStore: HistoryStore) {
        guard !FileManager.default.fileExists(atPath: markerURL.path) else { return }

        if let config = importLegacyConfig() {
            try? configStore.save(config)
        }

        importLegacyHistory(into: historyStore)

        FileManager.default.createFile(atPath: markerURL.path, contents: Data())
    }

    private func importLegacyConfig() -> VoiceFlowConfig? {
        let configPath = legacyDir.appendingPathComponent("config.toml")
        guard let content = try? String(contentsOf: configPath) else { return nil }

        var config = VoiceFlowConfig()
        var section = ""

        for rawLine in content.split(separator: "\n") {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("[") && line.hasSuffix("]") {
                section = String(line.dropFirst().dropLast())
                continue
            }
            guard let eq = line.firstIndex(of: "=") else { continue }
            let key = line[..<eq].trimmingCharacters(in: .whitespaces)
            let value = line[line.index(after: eq)...].trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "\""))

            switch (section, key) {
            case ("hotkey", "key"): config.hotkey = value
            case ("asr", "engine"): config.asrEngine = value
            case ("asr", "model"): config.asrModel = value
            case ("asr", "language"): config.asrLanguage = value
            case ("llm", "cleanup_level"): config.cleanupLevel = value
            case ("llm", "ollama_model"): config.ollamaModel = value
            case ("llm", "ollama_base_url"): config.ollamaBaseURL = value
            case ("llm", "docker_llm_url"): config.dockerLLMURL = value
            case ("injection", "method"): config.injectionMethod = value
            default: break
            }
        }

        return config
    }

    private func importLegacyHistory(into historyStore: HistoryStore) {
        let dbURL = legacyDir.appendingPathComponent("history.db")
        guard FileManager.default.fileExists(atPath: dbURL.path) else { return }

        var legacyDB: OpaquePointer?
        guard sqlite3_open(dbURL.path, &legacyDB) == SQLITE_OK else { return }
        defer { sqlite3_close(legacyDB) }

        let sql = "SELECT ts, raw, clean, level, app FROM entries ORDER BY id ASC;"
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(legacyDB, sql, -1, &stmt, nil) == SQLITE_OK else { return }
        defer { sqlite3_finalize(stmt) }

        while sqlite3_step(stmt) == SQLITE_ROW {
            guard let rawPtr = sqlite3_column_text(stmt, 1),
                  let cleanPtr = sqlite3_column_text(stmt, 2),
                  let levelPtr = sqlite3_column_text(stmt, 3) else {
                continue
            }
            let raw = String(cString: rawPtr)
            let clean = String(cString: cleanPtr)
            let level = String(cString: levelPtr)
            let appName = sqlite3_column_text(stmt, 4).map { String(cString: $0) }
            _ = historyStore.save(raw: raw, clean: clean, level: level, app: appName)
        }
    }
}
