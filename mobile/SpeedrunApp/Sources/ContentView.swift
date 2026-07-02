// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import SwiftUI
import WebKit

struct ContentView: View {
    @StateObject private var session = ReviewSession()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack(spacing: 16) {
            header

            Divider()

            switch session.phase {
            case .loading:
                Spacer()
                ProgressView("Loading…")
                Spacer()

            case .question:
                cardArea(html: session.questionHTML)
                Spacer()
                Button {
                    session.reveal()
                } label: {
                    Text("Show Answer")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("showAnswer")

            case .answer:
                cardArea(html: session.answerHTML)
                Spacer()
                gradeButtons

            case .finished:
                Spacer()
                VStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.largeTitle)
                        .foregroundColor(.green)
                    Text("Queue complete")
                        .font(.headline)
                    Text("\(session.reviewedCount) cards reviewed this session")
                        .foregroundColor(.secondary)
                }
                .accessibilityIdentifier("finished")
                Spacer()

            case let .error(message):
                Spacer()
                VStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.largeTitle)
                        .foregroundColor(.orange)
                    Text("Error").font(.headline)
                    ScrollView {
                        Text(message)
                            .font(.footnote.monospaced())
                            .multilineTextAlignment(.leading)
                            .padding()
                    }
                }
                .accessibilityIdentifier("error")
                Spacer()
            }
        }
        .padding()
        .onAppear { session.start() }
        .onChange(of: scenePhase) { newPhase in
            // Checkpoint graded progress into collection.anki2 when the app
            // leaves the foreground, so the on-disk database is always complete.
            if newPhase == .background { session.flush() }
        }
    }

    private var header: some View {
        VStack(spacing: 4) {
            Text("Speedrun PGRE")
                .font(.title2.bold())
            HStack(spacing: 16) {
                Label("\(session.reviewedCount)", systemImage: "checkmark.seal")
                    .accessibilityIdentifier("reviewedCount")
                Text("new \(session.newCount)")
                Text("lrn \(session.learnCount)")
                Text("rev \(session.reviewCount)")
            }
            .font(.caption)
            .foregroundColor(.secondary)
        }
    }

    private func cardArea(html: String) -> some View {
        CardWebView(bodyHTML: html)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityIdentifier("cardWeb")
    }

    private var gradeButtons: some View {
        HStack(spacing: 8) {
            ForEach(Rating.allCases) { rating in
                Button {
                    session.grade(rating)
                } label: {
                    Text(rating.label)
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .background(rating.color)
                .foregroundColor(.white)
                .cornerRadius(8)
                .accessibilityIdentifier("grade_\(rating.label)")
            }
        }
    }
}

/// Renders a card side's HTML in a `WKWebView`, typesetting any LaTeX with the
/// bundled MathJax (staged into Documents by `ReviewSession.prepareMathjax`).
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

    /// Wraps a card side's HTML in a minimal responsive page. MathJax's default
    /// delimiters already include `\(…\)` (what the formula deck uses); it finds
    /// its fonts relative to the script URL, so no extra config is needed.
    private static func document(body: String) -> String {
        let shown = body.isEmpty ? "<p style=\"opacity:.5\">(empty)</p>" : body
        return """
        <!doctype html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          :root { color-scheme: light dark; }
          body { font-family: -apple-system, system-ui, sans-serif; font-size: 22px;
                 line-height: 1.45; margin: 20px; background: transparent; color: #111; }
          @media (prefers-color-scheme: dark) { body { color: #eee; } }
          hr { border: none; border-top: 1px solid rgba(128,128,128,0.4); margin: 18px 0; }
          img { max-width: 100%; height: auto; }
          mjx-container { font-size: 118% !important; }
        </style>
        <script src="mathjax/tex-chtml-full.js" async></script>
        </head>
        <body>
        \(shown)
        </body>
        </html>
        """
    }
}
