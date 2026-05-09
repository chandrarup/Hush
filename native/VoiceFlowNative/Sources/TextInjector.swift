import Foundation
import Carbon.HIToolbox
import AppKit

protocol TextInjecting {
    func inject(_ text: String) -> Bool
}

final class PasteboardTextInjector: TextInjecting {
    func inject(_ text: String) -> Bool {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)

        guard let src = CGEventSource(stateID: .hidSystemState) else { return false }

        let down = CGEvent(keyboardEventSource: src, virtualKey: CGKeyCode(kVK_ANSI_V), keyDown: true)
        down?.flags = .maskCommand
        let up = CGEvent(keyboardEventSource: src, virtualKey: CGKeyCode(kVK_ANSI_V), keyDown: false)
        up?.flags = .maskCommand

        down?.post(tap: .cghidEventTap)
        up?.post(tap: .cghidEventTap)
        return true
    }
}
