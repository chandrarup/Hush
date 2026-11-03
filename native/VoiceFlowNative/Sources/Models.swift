import Foundation

enum PipelineState: String {
    case idle
    case recording
    case processing
    case failed
}

struct PipelineOutput {
    let rawText: String
    let cleanText: String
}

struct VoiceFlowConfig: Codable {
    var hotkey: String = "ctrl_r"
    var asrEngine: String = "auto"
    var asrModel: String = ""
    var asrLanguage: String = "en"
    var cleanupLevel: String = "light"
    var injectionMethod: String = "quartz"
    var ollamaModel: String = "llama3.2:3b"
    var ollamaBaseURL: String = "http://localhost:11434"
    var dockerLLMURL: String = "http://localhost:12434/engines/llama.cpp/v1"
}

struct HistoryEntry: Identifiable {
    let id: Int64
    let timestampISO8601: String
    let rawText: String
    let cleanText: String
    let cleanupLevel: String
    let appName: String?
}
