// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Pure view-model mapper for the Speedrun dashboard. No Svelte or backend
// imports — this module is unit-tested in isolation (lib.test.ts).
//
// The central invariant (SPECS.md S5-T02 "honesty guard"): the ONLY way to
// produce a "score" view model is when the backend did not abstain AND every
// honesty field is present and valid. If anything is missing or invalid we
// fall back to the "abstain" view, so it is structurally impossible for the
// component to render a bare score number without its range + confidence.

import type { TopicMasteryResponse } from "@generated/anki/speedrun_pb";

/** Thresholds echoed back from the backend (the "give-up rule"). */
export interface ThresholdsView {
    masteredThreshold: number;
    reviewFloor: number;
    coverageFloor: number;
}

/** One row in the per-topic table. */
export interface TopicRow {
    tag: string;
    name: string;
    weight: number;
    totalCards: number;
    cardsWithState: number;
    mastered: number;
    meanRetrievabilityPct: number;
    meanStabilityDays: number;
    medianLatencyMs: number;
}

/** Discriminated union: either we abstain, or we have a fully-formed score. */
export type DashboardView =
    | {
        kind: "abstain";
        reasons: string[];
        coveragePct: number;
        totalReviews: number;
        thresholds: ThresholdsView;
        topics: TopicRow[];
    }
    | {
        kind: "score";
        scorePct: number;
        lowPct: number;
        highPct: number;
        coveragePct: number;
        totalReviews: number;
        confidence: string;
        reasons: string[];
        updatedAt: Date;
        thresholds: ThresholdsView;
        topics: TopicRow[];
    };

function isFiniteNumber(n: unknown): n is number {
    return typeof n === "number" && Number.isFinite(n);
}

function toThresholdsView(resp: TopicMasteryResponse): ThresholdsView {
    const t = resp.thresholds;
    return {
        masteredThreshold: t ? t.masteredThreshold : 0,
        reviewFloor: t ? t.reviewFloor : 0,
        coverageFloor: t ? t.coverageFloor : 0,
    };
}

function pct(fraction: number): number {
    return Math.round(fraction * 100);
}

function mapTopics(resp: TopicMasteryResponse): TopicRow[] {
    return resp.topics.map((t) => ({
        tag: t.tag,
        name: t.name,
        weight: t.weight,
        totalCards: t.totalCards,
        cardsWithState: t.cardsWithState,
        mastered: t.mastered,
        meanRetrievabilityPct: pct(t.meanRetrievability),
        meanStabilityDays: t.meanStability,
        medianLatencyMs: t.medianLatencyMs,
    }));
}

/**
 * True only when the response carries a valid, range-bearing score. All 7
 * honesty fields must check out; otherwise the caller must abstain.
 */
function hasValidScore(resp: TopicMasteryResponse): boolean {
    // 1. memory_score finite and in [0,1]
    if (!isFiniteNumber(resp.memoryScore) || resp.memoryScore < 0 || resp.memoryScore > 1) {
        return false;
    }
    // 2. a finite range with low <= score <= high
    if (!isFiniteNumber(resp.scoreLow) || !isFiniteNumber(resp.scoreHigh)) {
        return false;
    }
    if (!(resp.scoreLow <= resp.memoryScore && resp.memoryScore <= resp.scoreHigh)) {
        return false;
    }
    // 3. finite coverage
    if (!isFiniteNumber(resp.coverage)) {
        return false;
    }
    // 4. non-empty confidence
    if (typeof resp.confidence !== "string" || resp.confidence.length === 0) {
        return false;
    }
    // 5. positive updated_at_millis (bigint)
    if (typeof resp.updatedAtMillis !== "bigint" || resp.updatedAtMillis <= 0n) {
        return false;
    }
    // 6. thresholds object present
    if (!resp.thresholds) {
        return false;
    }
    // 7. reasons present (an array)
    if (!Array.isArray(resp.reasons)) {
        return false;
    }
    return true;
}

export function toViewModel(resp: TopicMasteryResponse): DashboardView {
    const topics = mapTopics(resp);
    const thresholds = toThresholdsView(resp);
    const coveragePct = isFiniteNumber(resp.coverage) ? pct(resp.coverage) : 0;

    if (resp.abstain || !hasValidScore(resp)) {
        const reasons = Array.isArray(resp.abstainReasons) ? resp.abstainReasons : [];
        return {
            kind: "abstain",
            reasons,
            coveragePct,
            totalReviews: resp.totalReviews,
            thresholds,
            topics,
        };
    }

    return {
        kind: "score",
        scorePct: pct(resp.memoryScore),
        lowPct: pct(resp.scoreLow),
        highPct: pct(resp.scoreHigh),
        coveragePct,
        totalReviews: resp.totalReviews,
        confidence: resp.confidence,
        reasons: resp.reasons,
        updatedAt: new Date(Number(resp.updatedAtMillis)),
        thresholds,
        topics,
    };
}
