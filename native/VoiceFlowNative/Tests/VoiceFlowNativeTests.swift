import XCTest
@testable import VoiceFlowNative

final class VoiceFlowNativeTests: XCTestCase {
    func testDefaultConfigHasExpectedHotkey() {
        XCTAssertEqual(VoiceFlowConfig().hotkey, "ctrl_r")
    }
}
