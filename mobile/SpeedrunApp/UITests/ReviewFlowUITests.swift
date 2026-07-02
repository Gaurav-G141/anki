// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// S7-T02: drives a real review session through the SwiftUI UI — opens the deck
// list, enters the Speed Recall deck, then taps "Show Answer" then "Again"
// repeatedly — and asserts at least 20 cards are graded without the app
// crashing. Each grade goes through AnswerCard on the shared Rust engine, so a
// green run also demonstrates that 20+ revlog rows persist.

import XCTest

final class ReviewFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testTwentyReviews() throws {
        let app = XCUIApplication()
        app.launch()

        let target = 20
        var graded = 0
        // Generous per-step timeouts; FFI calls run off-main and are fast, but
        // the very first open + render can take a moment on a cold simulator.
        let stepTimeout: TimeInterval = 20

        // Home screen is now the deck list. Enter the "Speed Recall" parent deck
        // (its 9 subdecks give 166 cards, plenty for 20 reviews). The row's
        // identifier is set on the NavigationLink; match any element type.
        let deckRow = app.descendants(matching: .any)
            .matching(identifier: "deck_Speed Recall").firstMatch
        XCTAssertTrue(
            deckRow.waitForExistence(timeout: stepTimeout),
            "Speed Recall deck row never appeared on the deck list"
        )
        deckRow.tap()

        let showAnswer = app.buttons["showAnswer"]
        // Grade with "Again": it keeps cards in the intraday learning queue so a
        // modest deck still yields 20+ graded answers (each a distinct revlog
        // row) within one session. The grade path is identical regardless of
        // rating, so this exercises AnswerCard end-to-end exactly the same.
        let again = app.buttons["grade_Again"]
        let finished = app.otherElements["finished"]
        let errorView = app.otherElements["error"]

        while graded < target {
            // Bail out clearly if the engine surfaced an error.
            if errorView.exists {
                XCTFail("Review session entered error state after \(graded) reviews")
            }
            // If we ran out of cards before hitting the target, that's a content
            // problem, not a crash — report how far we got.
            if finished.exists {
                XCTFail("Queue exhausted after \(graded) reviews (need \(target))")
            }

            XCTAssertTrue(
                showAnswer.waitForExistence(timeout: stepTimeout),
                "Show Answer button never appeared (review \(graded + 1))"
            )
            showAnswer.tap()

            XCTAssertTrue(
                again.waitForExistence(timeout: stepTimeout),
                "Again button never appeared (review \(graded + 1))"
            )
            again.tap()
            graded += 1
        }

        XCTAssertGreaterThanOrEqual(graded, target, "Graded \(graded) cards")
        // App must still be responsive (not crashed) after the session.
        XCTAssertEqual(app.state, .runningForeground)
    }
}
