// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// The Scores screen: the three honest scores (Memory, Performance, Readiness)
// from the shared SpeedrunService.TopicMastery RPC. It renders EXACTLY what the
// desktop dashboard does, porting the honesty guard from
// ts/routes/speedrun-dashboard/lib.ts: a score is shown only when the backend
// did not abstain AND every honesty field is valid; otherwise the card abstains
// with reasons. It is therefore impossible to show a bare number without its
// range + confidence (Cannot-break rule #3: three separate scores, each ranged).

import SwiftUI

struct ScoresView: View {
    @ObservedObject var store: CollectionStore

    var body: some View {
        Group {
            if let m = store.mastery {
                content(m)
            } else if store.masteryLoading {
                ProgressView("Computing scores…")
            } else if let err = store.masteryError {
                errorView(err)
            } else {
                ProgressView("Computing scores…")
            }
        }
        .navigationTitle("Scores")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    store.fetchMastery()
                } label: {
                    if store.masteryLoading {
                        ProgressView()
                    } else {
                        Image(systemName: "arrow.clockwise")
                    }
                }
                .accessibilityIdentifier("refreshScores")
                .disabled(store.masteryLoading)
            }
        }
        .onAppear { store.fetchMastery() }
    }

    private func content(_ m: Anki_Speedrun_TopicMasteryResponse) -> some View {
        List {
            Section {
                fractionCard(
                    title: "Memory",
                    id: "memory",
                    abstain: m.abstain || !Self.validFraction(m.memoryScore, m.scoreLow, m.scoreHigh, m.confidence),
                    abstainReasons: m.abstainReasons,
                    score: m.memoryScore, low: m.scoreLow, high: m.scoreHigh,
                    confidence: m.confidence, reasons: m.reasons,
                    caption: "Fraction of studied cards currently retrievable (FSRS recall ≥ threshold)."
                )
            }
            Section {
                fractionCard(
                    title: "Performance",
                    id: "performance",
                    abstain: m.performanceAbstain || !Self.validFraction(m.performanceScore, m.performanceLow, m.performanceHigh, m.performanceConfidence),
                    abstainReasons: m.performanceAbstainReasons,
                    score: m.performanceScore, low: m.performanceLow, high: m.performanceHigh,
                    confidence: m.performanceConfidence, reasons: m.performanceReasons,
                    caption: "How often you answer studied cards correctly (graded Good or Easy). These are cards you've already seen — not new, unseen exam questions — so this likely runs higher than your real exam accuracy."
                )
            }
            Section {
                readinessCard(m)
            }
            Section("The give-up rule") {
                Text(giveUpText(m))
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }
            if !m.topics.isEmpty {
                subjectsSection(m)
            }
        }
    }

    // MARK: - Cards

    @ViewBuilder
    private func fractionCard(
        title: String, id: String, abstain: Bool, abstainReasons: [String],
        score: Float, low: Float, high: Float, confidence: String,
        reasons: [String], caption: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.headline)
            if abstain {
                Text("No score yet")
                    .font(.title2).foregroundColor(.secondary)
                    .accessibilityIdentifier("\(id)Abstain")
                reasonList(abstainReasons.isEmpty ? ["Not enough evidence for an honest score."] : abstainReasons)
            } else {
                Text("\(Self.pct(score))%")
                    .font(.system(size: 40, weight: .bold))
                    .accessibilityIdentifier("\(id)Score")
                Text("95% range: \(Self.pct(low))% – \(Self.pct(high))%")
                    .foregroundColor(.secondary)
                confidenceRow(confidence)
                if !reasons.isEmpty { reasonList(reasons, title: "Weakest") }
            }
            Text(caption).font(.caption).foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    private func readinessCard(_ m: Anki_Speedrun_TopicMasteryResponse) -> some View {
        let abstain = m.readinessAbstain
            || !Self.validScaled(m.readinessScore, m.readinessLow, m.readinessHigh, m.readinessConfidence)
        VStack(alignment: .leading, spacing: 6) {
            Text("Readiness").font(.headline)
            if abstain {
                Text("No score yet")
                    .font(.title2).foregroundColor(.secondary)
                    .accessibilityIdentifier("readinessAbstain")
                reasonList(m.readinessAbstainReasons.isEmpty
                    ? ["Not enough evidence to project an exam score."] : m.readinessAbstainReasons)
            } else {
                Text("\(Int(m.readinessScore.rounded()))")
                    .font(.system(size: 40, weight: .bold))
                    .accessibilityIdentifier("readinessScore")
                Text("range: \(Int(m.readinessLow.rounded())) – \(Int(m.readinessHigh.rounded()))")
                    .foregroundColor(.secondary)
                confidenceRow(m.readinessConfidence)
            }
            Text("An estimate of your PGRE scaled score (200–990), converted from your Performance score. The fewer of the exam's topics you've studied, the wider and less certain this range. A model estimate — not an actual exam score.")
                .font(.caption).foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }

    private func confidenceRow(_ confidence: String) -> some View {
        HStack(spacing: 6) {
            Text("Confidence").foregroundColor(.secondary)
            Text(confidence.capitalized).fontWeight(.medium)
        }
        .font(.subheadline)
    }

    @ViewBuilder
    private func reasonList(_ reasons: [String], title: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let title { Text(title).font(.caption).foregroundColor(.secondary) }
            ForEach(reasons, id: \.self) { r in
                Text("• \(r)").font(.caption).foregroundColor(.secondary)
            }
        }
    }

    private func subjectsSection(_ m: Anki_Speedrun_TopicMasteryResponse) -> some View {
        Section("Subjects") {
            ForEach(m.topics, id: \.tag) { t in
                HStack {
                    Text(t.name)
                    Spacer()
                    Text("\(t.mastered)/\(t.cardsWithState) mastered")
                        .font(.caption).foregroundColor(.secondary)
                }
            }
        }
    }

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.largeTitle).foregroundColor(.orange)
            Text("Couldn't compute scores").font(.headline)
            Text(msg).font(.footnote.monospaced()).foregroundColor(.secondary)
                .multilineTextAlignment(.center).padding()
            Button("Retry") { store.fetchMastery() }
        }
        .padding()
    }

    private func giveUpText(_ m: Anki_Speedrun_TopicMasteryResponse) -> String {
        let t = m.thresholds
        let floor = t.reviewFloor
        let cov = Int((t.coverageFloor * 100).rounded())
        let mastered = Int((t.masteredThreshold * 100).rounded())
        return "A score is only shown with at least \(floor) graded reviews and \(cov)% topic coverage "
            + "(mastered at recall ≥ \(mastered)%). Each score abstains on its own when its evidence is thin."
    }

    // MARK: - Honesty guards (mirrors ts/routes/speedrun-dashboard/lib.ts)

    static func pct(_ f: Float) -> Int { Int((f * 100).rounded()) }

    static func validFraction(_ score: Float, _ low: Float, _ high: Float, _ confidence: String) -> Bool {
        guard score.isFinite, score >= 0, score <= 1 else { return false }
        guard low.isFinite, high.isFinite else { return false }
        guard low <= score, score <= high else { return false }
        return !confidence.isEmpty
    }

    static func validScaled(_ score: Float, _ low: Float, _ high: Float, _ confidence: String) -> Bool {
        guard score.isFinite, score >= 200, score <= 990 else { return false }
        guard low.isFinite, high.isFinite else { return false }
        guard low <= score, score <= high else { return false }
        return !confidence.isEmpty
    }
}
