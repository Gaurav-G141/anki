<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import { deckMastery } from "@generated/backend";

    import Graph from "./Graph.svelte";
    import type { MasteryRow } from "./mastery";
    import { masteryTotals, toMasteryRows } from "./mastery";

    // Part of the shared graph-card prop set; this card fetches its own data.
    export let sourceData: unknown = undefined;
    void sourceData;

    let rows: MasteryRow[] | null = null;
    let error = "";

    // Snapshot (whole collection, per deck); independent of the search/period.
    deckMastery({ masteredThreshold: 0 })
        .then((resp) => (rows = toMasteryRows(resp.decks)))
        .catch((err) => (error = String(err)));

    $: totals = rows ? masteryTotals(rows) : null;
</script>

<Graph title="Mastered" subtitle="Cards mastered (current recall ≥ 90%) per deck">
    {#if error}
        <div class="msg">Couldn't load mastery data: {error}</div>
    {:else if rows === null}
        <div class="msg">Loading…</div>
    {:else if rows.length === 0}
        <div class="msg">No cards yet.</div>
    {:else}
        <table>
            <thead>
                <tr>
                    <th class="deck">Deck</th>
                    <th>Mastered</th>
                    <th>Total</th>
                    <th>%</th>
                    <th>Mean R</th>
                </tr>
            </thead>
            <tbody>
                {#each rows as row (row.deckName)}
                    <tr>
                        <td class="deck">{row.deckName}</td>
                        <td>{row.mastered}</td>
                        <td>{row.total}</td>
                        <td>{row.masteredPct}%</td>
                        <td>{row.withState > 0 ? `${row.meanRPct}%` : "—"}</td>
                    </tr>
                {/each}
                {#if totals}
                    <tr class="totals">
                        <td class="deck">All decks</td>
                        <td>{totals.mastered}</td>
                        <td>{totals.total}</td>
                        <td>{totals.masteredPct}%</td>
                        <td></td>
                    </tr>
                {/if}
            </tbody>
        </table>
    {/if}
</Graph>

<style lang="scss">
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    th,
    td {
        padding: 2px 8px;
        text-align: right;
    }
    th.deck,
    td.deck {
        text-align: left;
    }
    .totals {
        font-weight: bold;
        border-top: 1px solid currentColor;
    }
    .msg {
        text-align: center;
        opacity: 0.7;
    }
</style>
