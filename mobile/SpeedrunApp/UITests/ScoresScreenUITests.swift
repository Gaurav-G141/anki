// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Verifies the phone shows the THREE scores (Memory, Performance, Readiness),
// each with a range or an honest "No score yet" abstain — Cannot-break rule #3.
// Taps the chart.bar toolbar button, then asserts all three cards exist and each
// resolves to either a score element or an abstain element (never a bare number
// without a range, by construction of ScoresView's honesty guard).

import XCTest

final class ScoresScreenUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testThreeScoresShown() throws {
        let app = XCUIApplication()
        app.launch()

        let timeout: TimeInterval = 20

        let scoresButton = app.descendants(matching: .any)
            .matching(identifier: "scores").firstMatch
        XCTAssertTrue(
            scoresButton.waitForExistence(timeout: timeout),
            "Scores toolbar button never appeared"
        )
        scoresButton.tap()

        // All three score titles must be present.
        for title in ["Memory", "Performance", "Readiness"] {
            XCTAssertTrue(
                app.staticTexts[title].waitForExistence(timeout: timeout),
                "\(title) card never appeared on the Scores screen"
            )
        }

        // Each score must resolve to EITHER a real score or an honest abstain —
        // both acceptable; a card that shows neither would be a bug.
        for name in ["memory", "performance", "readiness"] {
            let score = app.descendants(matching: .any)
                .matching(identifier: "\(name)Score").firstMatch
            let abstain = app.descendants(matching: .any)
                .matching(identifier: "\(name)Abstain").firstMatch
            let shown = score.waitForExistence(timeout: timeout)
                || abstain.waitForExistence(timeout: 1)
            XCTAssertTrue(shown, "\(name) card showed neither a score nor an abstain")
        }

        XCTAssertEqual(app.state, .runningForeground)
    }
}
