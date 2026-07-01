// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Pure view-model mapping for the "Mastered" graph card (fork-specific).
// Kept free of Svelte/backend imports so it can be unit-tested directly.

/** Structural subset of the generated `DeckMastery` message we render. */
export interface DeckStat {
    deckName: string;
    totalCards: number;
    cardsWithState: number;
    mastered: number;
    meanRetrievability: number;
}

export interface MasteryRow {
    deckName: string;
    total: number;
    withState: number;
    mastered: number;
    /** mastered / total, as a whole-number percent (0 when the deck is empty). */
    masteredPct: number;
    /** mean current recall over cards with FSRS state, whole-number percent. */
    meanRPct: number;
}

function pct(numerator: number, denominator: number): number {
    return denominator > 0 ? Math.round((100 * numerator) / denominator) : 0;
}

/**
 * Map the backend per-deck stats to display rows. The backend already returns
 * decks sorted by name; we preserve that order.
 */
export function toMasteryRows(decks: readonly DeckStat[]): MasteryRow[] {
    return decks.map((d) => ({
        deckName: d.deckName,
        total: d.totalCards,
        withState: d.cardsWithState,
        mastered: d.mastered,
        masteredPct: pct(d.mastered, d.totalCards),
        meanRPct: Math.round(100 * d.meanRetrievability),
    }));
}

/** Collection-wide totals for a summary row. */
export function masteryTotals(rows: readonly MasteryRow[]): {
    total: number;
    mastered: number;
    masteredPct: number;
} {
    const total = rows.reduce((s, r) => s + r.total, 0);
    const mastered = rows.reduce((s, r) => s + r.mastered, 0);
    return { total, mastered, masteredPct: pct(mastered, total) };
}
