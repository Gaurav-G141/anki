<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { TopicMasteryResponse } from "@generated/anki/speedrun_pb";

    import { type DashboardView, toViewModel } from "./lib";

    export let resp: TopicMasteryResponse;

    // The view model is the single source of truth; the template can only ever
    // render a score number alongside its range + confidence (see lib.ts).
    let view: DashboardView;
    $: view = toViewModel(resp);

    function fmtUpdated(d: Date): string {
        try {
            return d.toLocaleString();
        } catch {
            return d.toISOString();
        }
    }
</script>

<div class="speedrun-dashboard">
    <h1>Speedrun dashboard</h1>

    <div class="cards">
        <!-- Memory score (or honest abstain) -->
        {#if view.kind === "abstain"}
            <div class="card score-card">
                <div class="card-title">Memory score</div>
                <div class="big-stat muted" data-testid="abstain">No score yet</div>
                <p class="explain">
                    Not enough evidence to give an honest score. Here's what is holding
                    it back:
                </p>
                {#if view.reasons.length > 0}
                    <ul class="reasons">
                        {#each view.reasons as reason}
                            <li>{reason}</li>
                        {/each}
                    </ul>
                {:else}
                    <p class="reasons-empty">No reasons reported.</p>
                {/if}
                <dl class="meta">
                    <dt>Coverage</dt>
                    <dd>{view.coveragePct}%</dd>
                    <dt>Graded reviews</dt>
                    <dd>{view.totalReviews}</dd>
                </dl>
                <p class="give-up-rule">
                    Give-up rule: a score is only shown with at least
                    {view.thresholds.reviewFloor} graded reviews and
                    {Math.round(view.thresholds.coverageFloor * 100)}% coverage
                    (mastered at recall ≥
                    {Math.round(view.thresholds.masteredThreshold * 100)}%).
                </p>
            </div>
        {:else}
            <div class="card score-card">
                <div class="card-title">Memory score</div>
                <div class="big-stat" data-testid="score">{view.scorePct}%</div>
                <div class="range">
                    95% range: {view.lowPct}% – {view.highPct}%
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd class="confidence conf-{view.confidence}">{view.confidence}</dd>
                    <dt>Coverage</dt>
                    <dd>{view.coveragePct}%</dd>
                    <dt>Graded reviews</dt>
                    <dd>{view.totalReviews}</dd>
                    <dt>Updated</dt>
                    <dd>{fmtUpdated(view.updatedAt)}</dd>
                </dl>
                {#if view.reasons.length > 0}
                    <div class="weakest">
                        <div class="weakest-title">Weakest subjects</div>
                        <ul class="reasons">
                            {#each view.reasons as reason}
                                <li>{reason}</li>
                            {/each}
                        </ul>
                    </div>
                {/if}
                <p class="give-up-rule">
                    Give-up rule: a score is only shown with at least
                    {view.thresholds.reviewFloor} graded reviews and
                    {Math.round(view.thresholds.coverageFloor * 100)}% coverage
                    (mastered at recall ≥
                    {Math.round(view.thresholds.masteredThreshold * 100)}%).
                </p>
            </div>
        {/if}

        <!-- Performance (demonstrated recall accuracy on graded reviews) -->
        <div class="card score-card">
            <div class="card-title">Performance</div>
            {#if view.performance.kind === "abstain"}
                <div class="big-stat muted" data-testid="performance-abstain">
                    No score yet
                </div>
                <p class="explain">
                    Not enough evidence for an honest accuracy estimate.
                </p>
                {#if view.performance.reasons.length > 0}
                    <ul class="reasons">
                        {#each view.performance.reasons as reason}
                            <li>{reason}</li>
                        {/each}
                    </ul>
                {/if}
            {:else}
                <div class="big-stat" data-testid="performance-score">
                    {view.performance.scorePct}%
                </div>
                <div class="range">
                    95% range: {view.performance.lowPct}% – {view.performance.highPct}%
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd class="confidence conf-{view.performance.confidence}">
                        {view.performance.confidence}
                    </dd>
                </dl>
                <p class="explain">
                    How often you answer studied cards correctly (graded Good or Easy).
                    These are cards you've already seen — not new, unseen exam questions
                    — so this likely runs higher than your real exam accuracy.
                </p>
            {/if}
        </div>

        <!-- Readiness (projected PGRE scaled score, 200–990) -->
        <div class="card score-card">
            <div class="card-title">Readiness</div>
            {#if view.readiness.kind === "abstain"}
                <div class="big-stat muted" data-testid="readiness-abstain">
                    No score yet
                </div>
                <p class="explain">Not enough evidence to project an exam score.</p>
                {#if view.readiness.reasons.length > 0}
                    <ul class="reasons">
                        {#each view.readiness.reasons as reason}
                            <li>{reason}</li>
                        {/each}
                    </ul>
                {/if}
            {:else}
                <div class="big-stat" data-testid="readiness-score">
                    {view.readiness.score}
                </div>
                <div class="range">
                    range: {view.readiness.low} – {view.readiness.high}
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd class="confidence conf-{view.readiness.confidence}">
                        {view.readiness.confidence}
                    </dd>
                </dl>
                <p class="explain">
                    An estimate of your PGRE scaled score (200–990), converted from your
                    Performance score. The fewer of the exam's topics you've studied,
                    the wider and less certain this range. A model estimate — not an
                    actual exam score.
                </p>
            {/if}
        </div>
    </div>

    <!-- Per-topic breakdown -->
    <h2>Subjects</h2>
    <table class="topics">
        <thead>
            <tr>
                <th>Subject</th>
                <th class="num">Total</th>
                <th class="num">With state</th>
                <th class="num">Mastered</th>
                <th class="num">Mean R</th>
                <th class="num">Median latency</th>
            </tr>
        </thead>
        <tbody>
            {#each view.topics as topic}
                <tr>
                    <td>{topic.name}</td>
                    <td class="num">{topic.totalCards}</td>
                    <td class="num">{topic.cardsWithState}</td>
                    <td class="num">{topic.mastered}</td>
                    <td class="num">{topic.meanRetrievabilityPct}%</td>
                    <td class="num">{topic.medianLatencyMs} ms</td>
                </tr>
            {/each}
        </tbody>
    </table>
</div>

<style lang="scss">
    .speedrun-dashboard {
        max-width: 60em;
        margin: 1em auto;
        padding: 0 1em;
        font-size: var(--font-size);
    }

    h1 {
        margin-bottom: 0.5em;
    }

    h2 {
        margin-top: 1.5em;
    }

    .cards {
        display: flex;
        flex-wrap: wrap;
        gap: 1em;
    }

    .card {
        flex: 1 1 16em;
        border: 1px solid var(--border);
        border-radius: var(--border-radius, 6px);
        padding: 1em;
        background: var(--canvas-elevated, transparent);
    }

    .card-title {
        font-weight: bold;
        margin-bottom: 0.25em;
    }

    .big-stat {
        font-size: 2.5em;
        font-weight: bold;
        line-height: 1.1;
    }

    .big-stat.muted {
        color: var(--fg-subtle, var(--fg-disabled));
        font-size: 1.5em;
    }

    .range {
        margin-top: 0.25em;
        color: var(--fg-subtle, inherit);
    }

    .meta {
        display: grid;
        grid-template-columns: auto auto;
        gap: 0.1em 1em;
        margin: 0.75em 0;
    }

    .meta dt {
        font-weight: normal;
        color: var(--fg-subtle, inherit);
    }

    .meta dd {
        margin: 0;
        text-align: right;
    }

    .confidence {
        text-transform: capitalize;
    }

    .reasons {
        margin: 0.25em 0 0.5em 1em;
        padding: 0;
    }

    .weakest-title {
        font-weight: bold;
        margin-top: 0.5em;
    }

    .give-up-rule {
        margin-top: 0.5em;
        font-size: 0.85em;
        color: var(--fg-subtle, inherit);
    }

    table.topics {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.5em;
    }

    table.topics th,
    table.topics td {
        border-bottom: 1px solid var(--border);
        padding: 0.35em 0.5em;
        text-align: left;
    }

    table.topics .num {
        text-align: right;
    }
</style>
