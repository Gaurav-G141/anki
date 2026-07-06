// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// The per-deck review screen (pushed from the deck list). Owns a deck-scoped
// `ReviewSession` bound to the app's single shared engine (`CollectionStore`).

import SwiftUI
import WebKit

struct ReviewView: View {
    @StateObject private var session: ReviewSession
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let deckName: String

    init(store: CollectionStore, deckId: Int64, deckName: String) {
        _session = StateObject(wrappedValue: ReviewSession(store: store, deckId: deckId))
        self.deckName = deckName
    }

    var body: some View {
        VStack(spacing: 16) {
            counts

            Divider().overlay(Palette.line)

            switch session.phase {
            case .loading:
                StatusState(kind: .loading("Loading…"))
                    .transition(.opacity)

            case .question:
                cardArea(html: session.questionHTML)
                    .transition(.opacity)
                showAnswerButton

            case .answer:
                cardArea(html: session.answerHTML)
                    .transition(.opacity)
                gradeButtons

            case .finished:
                Spacer()
                VStack(spacing: 10) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(Palette.ok)
                        .shadow(color: Palette.ok.opacity(0.5), radius: 14)
                    Text("Queue complete")
                        .font(.pgTitle)
                        .foregroundColor(Palette.text)
                    Text("\(session.reviewedCount) cards reviewed this session")
                        .font(.pgMono(12))
                        .foregroundColor(Palette.textDim)
                }
                .frame(maxWidth: .infinity)
                .transition(.opacity)
                .accessibilityIdentifier("finished")
                Spacer()

            case let .error(message):
                Spacer()
                VStack(spacing: 10) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 34))
                        .foregroundColor(Palette.warn)
                    Text("Error")
                        .font(.pgTitle)
                        .foregroundColor(Palette.text)
                    ScrollView {
                        Text(message)
                            .font(.pgMono(12))
                            .foregroundColor(Palette.textDim)
                            .multilineTextAlignment(.leading)
                            .padding()
                    }
                }
                .frame(maxWidth: .infinity)
                .transition(.opacity)
                .accessibilityIdentifier("error")
                Spacer()
            }
        }
        .padding()
        .background(Color.clear)
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.18), value: session.phase)
        .navigationTitle(deckName)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { session.start() }
    }

    private var counts: some View {
        HStack(spacing: 18) {
            Label("\(session.reviewedCount)", systemImage: "checkmark.seal")
                .font(.pgMono(12, weight: .semibold))
                .foregroundColor(Palette.textDim)
                .accessibilityIdentifier("reviewedCount")
            Spacer()
            countStat("NEW", Int(session.newCount), Palette.info)
            countStat("LRN", Int(session.learnCount), Palette.warn)
            countStat("REV", Int(session.reviewCount), Palette.ok)
        }
    }

    /// A mono eyebrow-label + tabular count, dimmed when zero.
    private func countStat(_ label: String, _ value: Int, _ color: Color) -> some View {
        HStack(spacing: 5) {
            Text(label)
                .font(.pgMono(10, weight: .semibold))
                .tracking(1.2)
                .foregroundColor(Palette.textFaint)
            Text("\(value)")
                .font(.pgMono(13, weight: .semibold))
                .monospacedDigit()
                .foregroundColor(value == 0 ? Palette.textFaint : color)
        }
    }

    private func cardArea(html: String) -> some View {
        CardWebView(bodyHTML: html)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .glassCard(padding: 12)
            .accessibilityIdentifier("cardWeb")
    }

    /// The one focal CTA — glowing cyan, prominent. Disabled for the first
    /// couple of seconds a card is shown (anti-spam), so answers can't be
    /// blitzed through without reading the question.
    private var showAnswerButton: some View {
        Button {
            session.reveal()
        } label: {
            Text(session.canReveal ? "Show Answer" : "Read the question…")
                .font(.pgMono(15, weight: .bold))
                .tracking(1)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 15)
        }
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(session.canReveal ? Palette.accent : Palette.accent.opacity(0.28)))
        .foregroundColor(Palette.space)
        .shadow(color: Palette.accent.opacity(session.canReveal ? 0.5 : 0), radius: 16)
        .disabled(!session.canReveal)
        .accessibilityIdentifier("showAnswer")
    }

    private var gradeButtons: some View {
        HStack(spacing: 10) {
            ForEach(Rating.allCases) { rating in
                Button {
                    session.grade(rating)
                } label: {
                    Text(rating.label)
                        .font(.pgMono(13, weight: .bold))
                        .tracking(0.5)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 13)
                }
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(rating.color.opacity(0.14)))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(rating.color, lineWidth: 1.2))
                .foregroundColor(rating.color)
                .shadow(color: rating.color.opacity(0.35), radius: 8)
                .accessibilityIdentifier("grade_\(rating.label)")
            }
        }
    }
}

/// Renders a card side's HTML in a `WKWebView`, typesetting any LaTeX with the
/// bundled MathJax (staged into Documents by `CollectionStore.prepareMathjax`).
/// Loading from a file in Documents — with read access to Documents — lets the
/// relative `mathjax/…` script + fonts resolve fully offline.
struct CardWebView: UIViewRepresentable {
    let bodyHTML: String

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let doc = Self.document(body: bodyHTML)
        let cardURL = docs.appendingPathComponent("card.html")
        do {
            try doc.write(to: cardURL, atomically: true, encoding: .utf8)
            webView.loadFileURL(cardURL, allowingReadAccessTo: docs)
        } catch {
            webView.loadHTMLString(doc, baseURL: nil)
        }
    }

    /// Wraps a card side's HTML in the shared Observatory document (transparent
    /// body, light-on-dark text, MathJax include) so the card matches the desktop
    /// hero pages and the iOS MCQ screen. MathJax's default delimiters already
    /// include `\(…\)` (what the formula deck uses).
    private static func document(body: String) -> String {
        let shown = body.isEmpty ? "<p style=\"opacity:.5\">(empty)</p>" : body
        return SpeedrunWeb.document(bodyHTML: shown, css: "", mjxScale: 118)
    }
}
