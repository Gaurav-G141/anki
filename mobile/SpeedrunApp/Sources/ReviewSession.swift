// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Drives a real review session against the shared Rust engine. All FFI calls
// run on a dedicated serial background queue; only view state is published on
// the main thread. Engine/collection state lives entirely in Rust.

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
        case .again: return .red
        case .hard: return .orange
        case .good: return .green
        case .easy: return .blue
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

    // Engine + current card live off the main thread; guarded by `queue`.
    private let queue = DispatchQueue(label: "net.ankiweb.speedrun.engine")
    private var engine: AnkiEngine?
    private var currentCard: Anki_Scheduler_QueuedCards.QueuedCard?
    /// CACurrentMediaTime() captured when the current question was shown.
    private var shownAt: CFTimeInterval = 0

    /// Opens the collection (copying the bundled deck to Documents on first
    /// launch) and fetches the first card. Safe to call once on appear.
    func start() {
        phase = .loading
        queue.async { [weak self] in
            guard let self else { return }
            do {
                let collectionPath = try Self.prepareCollectionPath()
                let mediaFolder = try Self.prepareMediaFolder()
                let mediaDB = Self.documentsURL().appendingPathComponent("collection.media.db").path

                var initProto = Anki_Backend_BackendInit()
                initProto.preferredLangs = []

                let engine = try AnkiEngine.open(init: initProto)

                var openReq = Anki_Collection_OpenCollectionRequest()
                openReq.collectionPath = collectionPath
                openReq.mediaFolderPath = mediaFolder
                openReq.mediaDbPath = mediaDB

                _ = try engine.command(
                    service: AnkiService.collection,
                    method: AnkiMethod.openCollection,
                    request: openReq,
                    response: Anki_Generic_Empty.self
                )
                self.engine = engine
                try self.fetchNextLocked()
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
        queue.async { [weak self] in
            guard let self, let engine = self.engine, let card = self.currentCard else { return }
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

                DispatchQueue.main.async { self.reviewedCount += 1 }
                try self.fetchNextLocked()
            } catch {
                self.publishError(error)
            }
        }
    }

    // MARK: - Engine helpers (run on `queue`)

    /// Fetches the next queued card and renders it, or marks the session
    /// finished if the queue is empty. Must run on `queue`.
    private func fetchNextLocked() throws {
        guard let engine = self.engine else { return }

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

        let q = Self.plainText(from: rendered.questionNodes)
        let a = Self.plainText(from: rendered.answerNodes)

        DispatchQueue.main.async {
            self.questionHTML = q
            self.answerHTML = a
            self.shownAt = CACurrentMediaTime()
            self.phase = .question
        }
    }

    private func publishError(_ error: Error) {
        DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
    }

    /// Concatenates rendered template nodes into a plain string, stripping the
    /// most common HTML tags so the minimal UI stays readable without a webview.
    private static func plainText(from nodes: [Anki_CardRendering_RenderedTemplateNode]) -> String {
        var out = ""
        for node in nodes {
            switch node.value {
            case let .text(t): out += t
            case let .replacement(r): out += r.currentText
            case .none: break
            }
        }
        return strippingHTML(out)
    }

    private static func strippingHTML(_ s: String) -> String {
        var result = s
        // Turn common block separators into newlines, then drop tags.
        for tag in ["<br>", "<br/>", "<br />", "</div>", "</p>", "<hr>", "<hr/>", "<hr id=answer>"] {
            result = result.replacingOccurrences(of: tag, with: "\n")
        }
        // Strip any remaining tags.
        var stripped = ""
        var inTag = false
        for ch in result {
            if ch == "<" { inTag = true; continue }
            if ch == ">" { inTag = false; continue }
            if !inTag { stripped.append(ch) }
        }
        // Decode a couple of frequent entities.
        stripped = stripped
            .replacingOccurrences(of: "&nbsp;", with: " ")
            .replacingOccurrences(of: "&amp;", with: "&")
            .replacingOccurrences(of: "&lt;", with: "<")
            .replacingOccurrences(of: "&gt;", with: ">")
        return stripped.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: - Filesystem setup

    private static func documentsURL() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    /// Copies the bundled `pgre_main.anki2` to `Documents/collection.anki2` on
    /// first launch, returning the destination path.
    private static func prepareCollectionPath() throws -> String {
        let dest = documentsURL().appendingPathComponent("collection.anki2")
        let fm = FileManager.default
        if !fm.fileExists(atPath: dest.path) {
            guard let bundled = Bundle.main.url(forResource: "pgre_main", withExtension: "anki2") else {
                throw AnkiEngineError.openBackendFailed("bundled deck pgre_main.anki2 not found in app bundle")
            }
            try fm.copyItem(at: bundled, to: dest)
        }
        return dest.path
    }

    private static func prepareMediaFolder() throws -> String {
        let media = documentsURL().appendingPathComponent("collection.media")
        let fm = FileManager.default
        if !fm.fileExists(atPath: media.path) {
            try fm.createDirectory(at: media, withIntermediateDirectories: true)
        }
        return media.path
    }
}
