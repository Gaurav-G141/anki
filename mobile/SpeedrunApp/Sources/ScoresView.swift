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
                StatusState(kind: .loading("Computing scores…"))
            } else if let err = store.masteryError {
                errorView(err)
            } else {
                StatusState(kind: .loading("Computing scores…"))
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
                    color: Palette.accent,
                    abstain: m.abstain || !Self.validFraction(m.memoryScore, m.scoreLow, m.scoreHigh, m.confidence),
                    abstainReasons: m.abstainReasons,
                    score: m.memoryScore, low: m.scoreLow, high: m.scoreHigh,
                    confidence: m.confidence, reasons: m.reasons,
                    caption: "Fraction of studied cards currently retrievable (FSRS recall ≥ threshold)."
                )
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
            Section {
                fractionCard(
                    title: "Performance",
                    id: "performance",
                    color: Palette.accent2,
                    abstain: m.performanceAbstain || !Self.validFraction(m.performanceScore, m.performanceLow, m.performanceHigh, m.performanceConfidence),
                    abstainReasons: m.performanceAbstainReasons,
                    score: m.performanceScore, low: m.performanceLow, high: m.performanceHigh,
                    confidence: m.performanceConfidence, reasons: m.performanceReasons,
                    caption: "How often you answer studied cards correctly (graded Good or Easy). These are cards you've already seen — not new, unseen exam questions — so this likely runs higher than your real exam accuracy."
                )
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
            Section {
                readinessCard(m)
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
            Section {
                Text(giveUpText(m))
                    .font(.footnote)
                    .foregroundColor(Palette.textDim)
            } header: {
                Eyebrow("The give-up rule")
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
            if !m.topics.isEmpty {
                subjectsSection(m)
            }
        }
    }

    // MARK: - Cards

    @ViewBuilder
    private func fractionCard(
        title: String, id: String, color: Color, abstain: Bool, abstainReasons: [String],
        score: Float, low: Float, high: Float, confidence: String,
        reasons: [String], caption: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title).font(.headline).foregroundColor(Palette.text)
            HStack(alignment: .center, spacing: 18) {
                if abstain {
                    GaugeRing(fraction: 0, color: color, dimmed: true) {
                        abstainCenter(id: "\(id)Abstain")
                    }
                    reasonList(abstainReasons.isEmpty ? ["Not enough evidence for an honest score."] : abstainReasons)
                } else {
                    GaugeRing(
                        fraction: Double(score),
                        band: Self.fractionBand(low, high),
                        color: color
                    ) {
                        scoreCenter(value: "\(Self.pct(score))", unit: "%", id: "\(id)Score", color: color)
                    }
                    VStack(alignment: .leading, spacing: 6) {
                        Text("95% range: \(Self.pct(low))% – \(Self.pct(high))%")
                            .font(.subheadline).foregroundColor(Palette.textDim)
                        confidenceRow(confidence)
                        if !reasons.isEmpty { reasonList(reasons, title: "Weakest") }
                    }
                }
            }
            Text(caption).font(.caption).foregroundColor(Palette.textDim)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassCard()
    }

    @ViewBuilder
    private func readinessCard(_ m: Anki_Speedrun_TopicMasteryResponse) -> some View {
        let abstain = m.readinessAbstain
            || !Self.validScaled(m.readinessScore, m.readinessLow, m.readinessHigh, m.readinessConfidence)
        VStack(alignment: .leading, spacing: 14) {
            Text("Readiness").font(.headline).foregroundColor(Palette.text)
            HStack(alignment: .center, spacing: 18) {
                if abstain {
                    GaugeRing(fraction: 0, color: Palette.ok, dimmed: true) {
                        abstainCenter(id: "readinessAbstain")
                    }
                    reasonList(m.readinessAbstainReasons.isEmpty
                        ? ["Not enough evidence to project an exam score."] : m.readinessAbstainReasons)
                } else {
                    GaugeRing(
                        fraction: Self.scaledFraction(m.readinessScore),
                        band: Self.scaledBand(m.readinessLow, m.readinessHigh),
                        color: Palette.ok
                    ) {
                        scoreCenter(
                            value: "\(Int(m.readinessScore.rounded()))",
                            unit: "SCALED", id: "readinessScore", color: Palette.ok)
                    }
                    VStack(alignment: .leading, spacing: 6) {
                        Text("range: \(Int(m.readinessLow.rounded())) – \(Int(m.readinessHigh.rounded()))")
                            .font(.subheadline).foregroundColor(Palette.textDim)
                        confidenceRow(m.readinessConfidence)
                    }
                }
            }
            Text("An estimate of your PGRE scaled score (200–990), converted from your Performance score. The fewer of the exam's topics you've studied, the wider and less certain this range. A model estimate — not an actual exam score.")
                .font(.caption).foregroundColor(Palette.textDim)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassCard()
    }

    // MARK: - Gauge centres

    private func scoreCenter(value: String, unit: String, id: String, color: Color) -> some View {
        VStack(spacing: 1) {
            Text(value)
                .font(.system(size: 34, weight: .bold))
                .monospacedDigit()
                .foregroundColor(Palette.text)
                .accessibilityIdentifier(id)
            Text(unit)
                .font(.pgMono(9))
                .tracking(1.2)
                .foregroundColor(color)
        }
    }

    private func abstainCenter(id: String) -> some View {
        VStack(spacing: 4) {
            Text("—")
                .font(.system(size: 30, weight: .bold))
                .foregroundColor(Palette.textFaint)
            Text("insufficient\nsignal")
                .font(.pgMono(9))
                .tracking(1.0)
                .multilineTextAlignment(.center)
                .foregroundColor(Palette.textFaint)
                .accessibilityIdentifier(id)
        }
    }

    private func confidenceRow(_ confidence: String) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Self.confidenceColor(confidence))
                .frame(width: 8, height: 8)
            Text("Confidence").foregroundColor(Palette.textDim)
            Text(confidence.capitalized).fontWeight(.medium).foregroundColor(Palette.text)
        }
        .font(.subheadline)
    }

    @ViewBuilder
    private func reasonList(_ reasons: [String], title: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let title { Eyebrow(title) }
            ForEach(reasons, id: \.self) { r in
                Text("• \(r)").font(.caption).foregroundColor(Palette.textDim)
            }
        }
    }

    private func subjectsSection(_ m: Anki_Speedrun_TopicMasteryResponse) -> some View {
        Section {
            ForEach(m.topics, id: \.tag) { t in
                let frac = t.cardsWithState > 0
                    ? Double(t.mastered) / Double(t.cardsWithState) : 0
                HStack(spacing: 12) {
                    Circle()
                        .fill(Palette.mastery(frac))
                        .frame(width: 10, height: 10)
                        .shadow(color: Palette.mastery(frac).opacity(0.6), radius: 4)
                    Text(t.name).foregroundColor(Palette.text)
                    Spacer()
                    Text("\(t.mastered)/\(t.cardsWithState) mastered")
                        .font(.pgMono(12)).foregroundColor(Palette.textDim)
                }
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
            }
        } header: {
            Eyebrow("Subjects")
        }
    }

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            StatusState(kind: .error("Couldn't compute scores\n\(msg)"))
                .fixedSize(horizontal: false, vertical: true)
            Button("Retry") { store.fetchMastery() }
                .tint(Palette.accent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func giveUpText(_ m: Anki_Speedrun_TopicMasteryResponse) -> String {
        let t = m.thresholds
        let floor = t.reviewFloor
        let cov = Int((t.coverageFloor * 100).rounded())
        let mastered = Int((t.masteredThreshold * 100).rounded())
        return "A score is only shown with at least \(floor) graded reviews and \(cov)% topic coverage "
            + "(mastered at recall ≥ \(mastered)%). Each score abstains on its own when its evidence is thin."
    }

    // MARK: - Gauge geometry (visual only — never gates whether a number shows)

    /// A fraction score (0…1) low…high mapped to the ring's 0…1 sweep, clamped.
    static func fractionBand(_ low: Float, _ high: Float) -> ClosedRange<Double> {
        let lo = clamp01(Double(low))
        let hi = max(lo, clamp01(Double(high)))
        return lo...hi
    }

    /// A scaled score (200…990) mapped into the ring's 0…1 sweep.
    static func scaledFraction(_ v: Float) -> Double {
        clamp01((Double(v) - 200) / 790)
    }

    static func scaledBand(_ low: Float, _ high: Float) -> ClosedRange<Double> {
        let lo = scaledFraction(low)
        let hi = max(lo, scaledFraction(high))
        return lo...hi
    }

    private static func clamp01(_ v: Double) -> Double { min(max(v, 0), 1) }

    /// Confidence pip colour: high → green, medium → amber, else dim.
    static func confidenceColor(_ confidence: String) -> Color {
        switch confidence.lowercased() {
        case "high": return Palette.ok
        case "medium", "moderate": return Palette.warn
        default: return Palette.textFaint
        }
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
