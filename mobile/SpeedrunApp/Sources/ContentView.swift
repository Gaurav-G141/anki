// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import SwiftUI

struct ContentView: View {
    @StateObject private var session = ReviewSession()

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
                cardArea(front: session.questionHTML, back: nil)
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
                cardArea(front: session.questionHTML, back: session.answerHTML)
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

    private func cardArea(front: String, back: String?) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(front.isEmpty ? "(empty front)" : front)
                    .font(.title3)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if let back {
                    Divider()
                    Text(back.isEmpty ? "(empty back)" : back)
                        .font(.title3)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .accessibilityIdentifier("answerText")
                }
            }
            .padding()
        }
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
