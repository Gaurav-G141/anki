// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Verifies the Practice-MCQs (Performance) screen is reachable and opens without
// crashing. The quiz + AI-coach UI lives inside a WKWebView, whose inner DOM is
// NOT exposed to XCUITest accessibility — so the grading/coaching flow itself is
// covered by the HeuristicCoach unit tests + a manual simulator check, not here.
// This test only guards the native entry point + that the screen stays alive.

import XCTest

final class MCQScreenUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testMCQScreenOpens() throws {
        let app = XCUIApplication()
        app.launch()

        let timeout: TimeInterval = 20
        let mcqButton = app.descendants(matching: .any)
            .matching(identifier: "openMCQ").firstMatch
        XCTAssertTrue(
            mcqButton.waitForExistence(timeout: timeout),
            "Practice-MCQs toolbar button never appeared"
        )
        mcqButton.tap()

        // The screen hosts a WKWebView (opaque to XCUITest); assert we navigated
        // (the "Practice MCQs" nav title shows) and the app stays foreground.
        XCTAssertTrue(
            app.navigationBars["Practice MCQs"].waitForExistence(timeout: timeout),
            "Did not navigate to the Practice MCQs screen"
        )
        XCTAssertEqual(app.state, .runningForeground)
    }
}
