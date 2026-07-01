// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { expect, test } from "vitest";

import type { DeckStat } from "./mastery";
import { masteryTotals, toMasteryRows } from "./mastery";

const decks: DeckStat[] = [
    { deckName: "Alpha", totalCards: 10, cardsWithState: 8, mastered: 6, meanRetrievability: 0.83 },
    { deckName: "Beta", totalCards: 4, cardsWithState: 0, mastered: 0, meanRetrievability: 0 },
];

test("maps per-deck stats to display rows with percentages", () => {
    const rows = toMasteryRows(decks);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
        deckName: "Alpha",
        total: 10,
        withState: 8,
        mastered: 6,
        masteredPct: 60, // 6/10
        meanRPct: 83,
    });
    // empty-state deck: no divide-by-zero, percentages are 0
    expect(rows[1]).toMatchObject({ deckName: "Beta", masteredPct: 0, meanRPct: 0 });
});

test("preserves backend ordering", () => {
    const rows = toMasteryRows(decks);
    expect(rows.map((r) => r.deckName)).toStrictEqual(["Alpha", "Beta"]);
});

test("computes collection-wide totals", () => {
    const totals = masteryTotals(toMasteryRows(decks));
    expect(totals).toStrictEqual({ total: 14, mastered: 6, masteredPct: 43 }); // 6/14 ≈ 43%
});

test("handles an empty collection", () => {
    expect(toMasteryRows([])).toStrictEqual([]);
    expect(masteryTotals([])).toStrictEqual({ total: 0, mastered: 0, masteredPct: 0 });
});
