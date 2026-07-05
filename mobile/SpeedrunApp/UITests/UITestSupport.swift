// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Shared XCUITest helpers. SwiftUI `List`/`ScrollView` render their rows lazily,
// so an element below the fold is absent from the accessibility tree until it is
// scrolled near the viewport. These helpers scroll it into view first, so the
// tests assert *reachability*, not merely "happens to be on the first screen"
// (which depends on the simulator's screen height and how many decks/cards seed).

import XCTest

extension XCUIApplication {
    /// Swipe up (down the content) until `element` is present in the query tree,
    /// up to `maxSwipes` times. Returns whether it ended up present. No-op if the
    /// element is already there. Use for top-to-bottom traversals.
    @discardableResult
    func scrollUp(to element: XCUIElement, maxSwipes: Int = 10) -> Bool {
        var swipes = 0
        while !element.exists && swipes < maxSwipes {
            swipeUp()
            swipes += 1
        }
        return element.exists
    }

    /// Wait briefly, then scroll `element` into view. Convenience combining a cold-
    /// start wait (first render can lag on a fresh simulator) with `scrollUp`.
    @discardableResult
    func revealElement(_ element: XCUIElement, firstWait: TimeInterval = 8, maxSwipes: Int = 10) -> Bool {
        _ = element.waitForExistence(timeout: firstWait)
        return scrollUp(to: element, maxSwipes: maxSwipes)
    }
}
