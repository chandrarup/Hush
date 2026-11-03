import Foundation

enum PipelineError: Error {
    case notImplemented
    case emptyText
}

protocol TranscriptionPipeline {
    func startRecording() throws
    func stopRecordingAndTranscribe() async throws -> PipelineOutput
}

final class NativeTranscriptionPipeline: TranscriptionPipeline {
    func startRecording() throws {
        // TODO: wire AVAudioEngine capture pipeline.
    }

    func stopRecordingAndTranscribe() async throws -> PipelineOutput {
        // TODO: wire VAD + ASR + LLM cleanup services.
        throw PipelineError.notImplemented
    }
}
