// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { TopicMasteryResponse } from "@generated/anki/speedrun_pb";
import { describe, expect, test } from "vitest";

import { toViewModel } from "./lib";

const NINE_TOPICS = Array.from({ length: 9 }, (_, i) => ({
    tag: `tag${i}`,
    name: `Subject ${i}`,
    weight: 1 / 9,
    totalCards: 10 + i,
    cardsWithState: 5 + i,
    mastered: i,
    meanRetrievability: 0.5,
    meanStability: 12.3,
    medianLatencyMs: 1500 + i,
}));

/** A fully-valid, scored response. */
function validScored(): TopicMasteryResponse {
    return new TopicMasteryResponse({
        abstain: false,
        abstainReasons: [],
        memoryScore: 0.8,
        scoreLow: 0.72,
        scoreHigh: 0.86,
        coverage: 0.65,
        totalReviews: 240,
        confidence: "high",
        reasons: ["Subject 3 is weak", "Subject 7 is weak"],
        updatedAtMillis: 1_700_000_000_000n,
        thresholds: {
            masteredThreshold: 0.9,
            reviewFloor: 20,
            coverageFloor: 0.4,
        },
        topics: NINE_TOPICS,
    });
}

/** An abstaining response. */
function abstaining(): TopicMasteryResponse {
    return new TopicMasteryResponse({
        abstain: true,
        abstainReasons: ["Only 4 graded reviews (need 20)", "Coverage 10% (need 40%)"],
        coverage: 0.1,
        totalReviews: 4,
        thresholds: {
            masteredThreshold: 0.9,
            reviewFloor: 20,
            coverageFloor: 0.4,
        },
        topics: NINE_TOPICS,
    });
}

describe("S5-T01 mapping", () => {
    test("abstain proto maps to abstain view with reasons", () => {
        const view = toViewModel(abstaining());
        expect(view.kind).toBe("abstain");
        if (view.kind !== "abstain") {
            throw new Error("expected abstain");
        }
        expect(view.reasons).toEqual([
            "Only 4 graded reviews (need 20)",
            "Coverage 10% (need 40%)",
        ]);
        expect(view.coveragePct).toBe(10);
        expect(view.totalReviews).toBe(4);
        expect(view.thresholds.reviewFloor).toBe(20);
        expect(view.topics).toHaveLength(9);
    });

    test("valid proto maps to score view with correct percentages", () => {
        const view = toViewModel(validScored());
        expect(view.kind).toBe("score");
        if (view.kind !== "score") {
            throw new Error("expected score");
        }
        expect(view.scorePct).toBe(80);
        expect(view.lowPct).toBe(72);
        expect(view.highPct).toBe(86);
        expect(view.coveragePct).toBe(65);
        expect(view.confidence).toBe("high");
        expect(view.reasons).toEqual(["Subject 3 is weak", "Subject 7 is weak"]);
        expect(view.updatedAt.getTime()).toBe(1_700_000_000_000);
        expect(view.topics).toHaveLength(9);
        // per-topic mapping incl. median latency (S8) and mean R %
        expect(view.topics[0].medianLatencyMs).toBe(1500);
        expect(view.topics[0].meanRetrievabilityPct).toBe(50);
    });
});

describe("S5-T02 honesty guard", () => {
    // Each entry mutates one honesty field into an invalid state while keeping
    // abstain:false. The mapper must still refuse to produce a "score".
    const breakers: Array<[string, (r: TopicMasteryResponse) => void]> = [
        ["memoryScore not finite", (r) => (r.memoryScore = NaN)],
        ["memoryScore out of [0,1]", (r) => (r.memoryScore = 1.5)],
        ["scoreLow not finite", (r) => (r.scoreLow = NaN)],
        ["scoreHigh not finite", (r) => (r.scoreHigh = Infinity)],
        ["range does not bracket score (low > score)", (r) => (r.scoreLow = 0.95)],
        ["range does not bracket score (high < score)", (r) => (r.scoreHigh = 0.5)],
        ["coverage not finite", (r) => (r.coverage = NaN)],
        ["confidence empty", (r) => (r.confidence = "")],
        ["updatedAtMillis not positive", (r) => (r.updatedAtMillis = 0n)],
        ["thresholds missing", (r) => (r.thresholds = undefined)],
        ["reasons not an array", (r) => ((r as unknown as { reasons: unknown }).reasons = null)],
    ];

    for (const [label, mutate] of breakers) {
        test(`abstain:false but ${label} → abstain`, () => {
            const r = validScored();
            mutate(r);
            expect(r.abstain).toBe(false);
            const view = toViewModel(r);
            expect(view.kind).toBe("abstain");
        });
    }

    test("control: untouched valid proto still scores", () => {
        expect(toViewModel(validScored()).kind).toBe("score");
    });
});
