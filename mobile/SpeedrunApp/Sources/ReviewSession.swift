// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Drives a real, DECK-SCOPED review session against the shared Rust engine
// owned by `CollectionStore`. It borrows the store's single engine + serial
// queue (it does NOT open its own) so the whole app uses one engine. All FFI
// runs on that queue; only view state is published on the main thread.

import Foundation
import QuartzCore
import SwiftProtobuf
import SwiftUI

/// One of the four grades.
enum Rating: Int, CaseIterable, Identifiable {
    case again = 0
    case hard = 1
    case good = 2
    case easy = 3

    var id: Int { rawValue }

    var label: String {
        switch self {
        case .again: return "Again"
        case .hard: return "Hard"
        case .good: return "Good"
        case .easy: return "Easy"
        }
    }

    var proto: Anki_Scheduler_CardAnswer.Rating {
        switch self {
        case .again: return .again
        case .hard: return .hard
        case .good: return .good
        case .easy: return .easy
        }
    }

    var color: Color {
        switch self {
        case .again: return Palette.bad
        case .hard: return Palette.warn
        case .good: return Palette.ok
        case .easy: return Palette.info
        }
    }
}

@MainActor
final class ReviewSession: ObservableObject {
    enum Phase: Equatable {
        case loading
        case question
        case answer
        case finished
        case error(String)
    }

    @Published private(set) var phase: Phase = .loading
    @Published private(set) var questionHTML: String = ""
    @Published private(set) var answerHTML: String = ""
    /// Count of answers graded and persisted this session.
    @Published private(set) var reviewedCount: Int = 0
    /// Remaining queue counts, for a small status line.
    @Published private(set) var newCount: UInt32 = 0
    @Published private(set) var learnCount: UInt32 = 0
    @Published private(set) var reviewCount: UInt32 = 0

    /// The shared engine owner (one engine for the whole app) and the deck this
    /// session studies.
    private let store: CollectionStore
    private let deckId: Int64
    private var currentCard: Anki_Scheduler_QueuedCards.QueuedCard?
    /// CACurrentMediaTime() captured when the current question was shown.
    private var shownAt: CFTimeInterval = 0

    init(store: CollectionStore, deckId: Int64) {
        self.store = store
        self.deckId = deckId
    }

    /// Selects this session's deck as the current deck, then fetches the first
    /// card. The scheduler queue is scoped to the current deck (+ children), so
    /// this makes review deck-scoped. Safe to call once on appear.
    func start() {
        phase = .loading
        store.queue.async { [weak self] in
            guard let self else { return }
            guard let engine = self.store.engine else {
                self.publishError(AnkiEngineError.usageError("engine not open"))
                return
            }
            do {
                var deckReq = Anki_Decks_DeckId()
                deckReq.did = self.deckId
                _ = try engine.command(
                    service: AnkiService.decks,
                    method: AnkiMethod.setCurrentDeck,
                    request: deckReq,
                    response: Anki_Collection_OpChanges.self
                )
                try self.fetchNextLocked(engine: engine)
            } catch {
                self.publishError(error)
            }
        }
    }

    /// Reveals the answer; records nothing yet (timing continues).
    func reveal() {
        guard phase == .question else { return }
        phase = .answer
    }

    /// Grades the current card with the chosen rating, persists via AnswerCard,
    /// then fetches the next card.
    func grade(_ rating: Rating) {
        guard phase == .answer else { return }
        let elapsedMillis = UInt32(max(0, (CACurrentMediaTime() - shownAt) * 1000.0))
        phase = .loading
        store.queue.async { [weak self] in
            guard let self, let engine = self.store.engine, let card = self.currentCard else { return }
            do {
                let states = card.states
                let newState: Anki_Scheduler_SchedulingState
                switch rating {
                case .again: newState = states.again
                case .hard: newState = states.hard
                case .good: newState = states.good
                case .easy: newState = states.easy
                }

                var answer = Anki_Scheduler_CardAnswer()
                answer.cardID = card.card.id
                answer.currentState = states.current
                answer.newState = newState
                answer.rating = rating.proto
                answer.answeredAtMillis = Int64(Date().timeIntervalSince1970 * 1000.0)
                answer.millisecondsTaken = elapsedMillis

                _ = try engine.command(
                    service: AnkiService.scheduler,
                    method: AnkiMethod.answerCard,
                    request: answer,
                    response: Anki_Collection_OpChanges.self
                )

                DispatchQueue.main.async {
                    self.reviewedCount += 1
                    // Flag unsynced local progress so it auto-syncs on reconnect.
                    self.store.markReviewed()
                }
                try self.fetchNextLocked(engine: engine)
            } catch {
                self.publishError(error)
            }
        }
    }

    // MARK: - Engine helpers (run on the store's queue)

    /// Fetches the next queued card and renders it, or marks the session
    /// finished if the queue is empty. Must run on the store's `queue`.
    private func fetchNextLocked(engine: AnkiEngine) throws {
        var req = Anki_Scheduler_GetQueuedCardsRequest()
        req.fetchLimit = 1
        req.intradayLearningOnly = false

        let queued = try engine.command(
            service: AnkiService.scheduler,
            method: AnkiMethod.getQueuedCards,
            request: req,
            response: Anki_Scheduler_QueuedCards.self
        )

        DispatchQueue.main.async {
            self.newCount = queued.newCount
            self.learnCount = queued.learningCount
            self.reviewCount = queued.reviewCount
        }

        guard let card = queued.cards.first else {
            self.currentCard = nil
            DispatchQueue.main.async { self.phase = .finished }
            return
        }
        self.currentCard = card

        // Render question + answer HTML via the engine (RenderExistingCard).
        var renderReq = Anki_CardRendering_RenderExistingCardRequest()
        renderReq.cardID = card.card.id
        renderReq.browser = false
        renderReq.partialRender = false

        let rendered = try engine.command(
            service: AnkiService.cardRendering,
            method: AnkiMethod.renderExistingCard,
            request: renderReq,
            response: Anki_CardRendering_RenderCardResponse.self
        )

        let q = Self.htmlString(from: rendered.questionNodes)
        let a = Self.htmlString(from: rendered.answerNodes)

        // Test/demo hook: SPEEDRUN_AUTOREVEAL=1 starts each card on the answer
        // side (so screenshots can show the typeset formula). Off in normal use.
        let autoReveal = ProcessInfo.processInfo.environment["SPEEDRUN_AUTOREVEAL"] == "1"
        DispatchQueue.main.async {
            self.questionHTML = q
            self.answerHTML = a
            self.shownAt = CACurrentMediaTime()
            self.phase = autoReveal ? .answer : .question
        }
    }

    private func publishError(_ error: Error) {
        DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
    }

    /// Concatenates rendered template nodes into the card side's HTML, keeping
    /// the markup so the WebView can style it and MathJax can typeset the LaTeX.
    private static func htmlString(from nodes: [Anki_CardRendering_RenderedTemplateNode]) -> String {
        var out = ""
        for node in nodes {
            switch node.value {
            case let .text(t): out += t
            case let .replacement(r): out += r.currentText
            case .none: break
            }
        }
        return out
    }
}
