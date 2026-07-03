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
    accuracyPct: number;
}

/** A [0,1]-fraction score (Memory, Performance): either abstain or a ranged %. */
export type FractionScoreView =
    | { kind: "abstain"; reasons: string[] }
    | {
        kind: "score";
        scorePct: number;
        lowPct: number;
        highPct: number;
        confidence: string;
        reasons: string[];
    };

/** The Readiness score, projected onto the 200–990 ETS scale. */
export type ScaledScoreView =
    | { kind: "abstain"; reasons: string[] }
    | {
        kind: "score";
        score: number;
        low: number;
        high: number;
        confidence: string;
        reasons: string[];
    };

/** Discriminated union: either we abstain, or we have a fully-formed score. */
export type DashboardView =
    | {
        kind: "abstain";
        reasons: string[];
        coveragePct: number;
        totalReviews: number;
        thresholds: ThresholdsView;
        topics: TopicRow[];
        performance: FractionScoreView;
        readiness: ScaledScoreView;
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
        performance: FractionScoreView;
        readiness: ScaledScoreView;
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
        accuracyPct: pct(t.accuracy),
    }));
}

/** A finite fraction in [0,1]. */
function isFraction(n: unknown): n is number {
    return isFiniteNumber(n) && n >= 0 && n <= 1;
}

/** Shared honesty check for a ranged fraction score (Memory / Performance). */
function validFractionScore(
    score: number,
    low: number,
    high: number,
    confidence: string,
): boolean {
    if (!isFraction(score)) {
        return false;
    }
    if (!isFiniteNumber(low) || !isFiniteNumber(high)) {
        return false;
    }
    if (!(low <= score && score <= high)) {
        return false;
    }
    return typeof confidence === "string" && confidence.length > 0;
}

/** Honesty check for the 200–990 readiness score. */
function validScaledScore(
    score: number,
    low: number,
    high: number,
    confidence: string,
): boolean {
    if (!isFiniteNumber(score) || score < 200 || score > 990) {
        return false;
    }
    if (!isFiniteNumber(low) || !isFiniteNumber(high)) {
        return false;
    }
    if (!(low <= score && score <= high)) {
        return false;
    }
    return typeof confidence === "string" && confidence.length > 0;
}

/**
 * Performance sub-view. Abstains if the backend abstained OR any honesty field
 * is invalid — so the component can never render a bare Performance number.
 */
function performanceView(resp: TopicMasteryResponse): FractionScoreView {
    const reasons = Array.isArray(resp.performanceAbstainReasons)
        ? resp.performanceAbstainReasons
        : [];
    if (
        resp.performanceAbstain
        || !validFractionScore(
            resp.performanceScore,
            resp.performanceLow,
            resp.performanceHigh,
            resp.performanceConfidence,
        )
    ) {
        return { kind: "abstain", reasons };
    }
    return {
        kind: "score",
        scorePct: pct(resp.performanceScore),
        lowPct: pct(resp.performanceLow),
        highPct: pct(resp.performanceHigh),
        confidence: resp.performanceConfidence,
        reasons: Array.isArray(resp.performanceReasons) ? resp.performanceReasons : [],
    };
}

/** Readiness sub-view; same honesty guard on the 200–990 scale. */
function readinessView(resp: TopicMasteryResponse): ScaledScoreView {
    const reasons = Array.isArray(resp.readinessAbstainReasons)
        ? resp.readinessAbstainReasons
        : [];
    if (
        resp.readinessAbstain
        || !validScaledScore(
            resp.readinessScore,
            resp.readinessLow,
            resp.readinessHigh,
            resp.readinessConfidence,
        )
    ) {
        return { kind: "abstain", reasons };
    }
    return {
        kind: "score",
        score: Math.round(resp.readinessScore),
        low: Math.round(resp.readinessLow),
        high: Math.round(resp.readinessHigh),
        confidence: resp.readinessConfidence,
        reasons: Array.isArray(resp.readinessReasons) ? resp.readinessReasons : [],
    };
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
    // Each score is derived independently (Cannot-break rule #3): three separate
    // scores, each with its own range + abstain, never one blended number.
    const performance = performanceView(resp);
    const readiness = readinessView(resp);

    if (resp.abstain || !hasValidScore(resp)) {
        const reasons = Array.isArray(resp.abstainReasons) ? resp.abstainReasons : [];
        return {
            kind: "abstain",
            reasons,
            coveragePct,
            totalReviews: resp.totalReviews,
            thresholds,
            topics,
            performance,
            readiness,
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
        performance,
        readiness,
    };
}
