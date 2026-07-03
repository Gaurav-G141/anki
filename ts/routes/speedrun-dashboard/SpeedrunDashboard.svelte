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

    // ---- Observatory gauge geometry -------------------------------------
    // A 270° open-bottom gauge ring drawn as SVG arc paths. All positions are
    // computed from the score fraction; nothing here decides abstain-vs-score
    // (that stays in lib.ts / the honesty guard).
    const CX = 60;
    const CY = 60;
    const R = 46;
    const START = 135; // degrees; bottom-left, sweeping clockwise
    const SWEEP = 270; // open gap at the bottom

    function clamp01(t: number): number {
        return Math.min(1, Math.max(0, t));
    }

    function polarX(deg: number, r: number): number {
        return CX + r * Math.cos((deg * Math.PI) / 180);
    }

    function polarY(deg: number, r: number): number {
        return CY + r * Math.sin((deg * Math.PI) / 180);
    }

    /** SVG arc path over the gauge sweep, with t0/t1 in [0,1]. */
    function arcPath(t0: number, t1: number): string {
        const a0 = START + SWEEP * clamp01(t0);
        const a1 = START + SWEEP * clamp01(t1);
        if (a1 <= a0) {
            return "";
        }
        const large = a1 - a0 > 180 ? 1 : 0;
        const x0 = polarX(a0, R).toFixed(2);
        const y0 = polarY(a0, R).toFixed(2);
        const x1 = polarX(a1, R).toFixed(2);
        const y1 = polarY(a1, R).toFixed(2);
        return `M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1}`;
    }

    function lerp(a: number, b: number, t: number): number {
        return Math.round(a + (b - a) * t);
    }

    /** Red → amber → green emission ramp (matches the Observatory tokens). */
    function masteryColor(t: number): string {
        const c = clamp01(t);
        let r: number;
        let g: number;
        let b: number;
        if (c <= 0.5) {
            const u = c / 0.5;
            r = lerp(255, 245, u);
            g = lerp(76, 177, u);
            b = lerp(76, 76, u);
        } else {
            const u = (c - 0.5) / 0.5;
            r = lerp(245, 61, u);
            g = lerp(177, 214, u);
            b = lerp(76, 140, u);
        }
        return `rgb(${r}, ${g}, ${b})`;
    }

    /** Map a 200–990 scaled score onto the gauge's [0,1] sweep. */
    function readinessT(v: number): number {
        return clamp01((v - 200) / (990 - 200));
    }

    interface GaugeArgs {
        abstain: boolean;
        display: string;
        valueT: number;
        lowT: number;
        highT: number;
        color: string;
        confidence: string | null;
        testid: string;
        label: string;
    }
</script>

<!-- One reusable gauge ring: background track, 95% Wilson band (fainter,
     wider arc), value arc, centered tabular number, and a confidence pip.
     The centered number + confidence text stay in the DOM for screen
     readers; the whole ring carries a text alternative via aria-label. -->
{#snippet gauge(g: GaugeArgs)}
    <div class="gauge" class:abstain={g.abstain}>
        <svg viewBox="0 0 120 120" role="img" aria-label={g.label}>
            <path class="track" d={arcPath(0, 1)} />
            {#if !g.abstain}
                {#if g.highT > g.lowT}
                    <path class="band" d={arcPath(g.lowT, g.highT)} stroke={g.color} />
                {/if}
                {#if g.valueT > 0}
                    <path class="value" d={arcPath(0, g.valueT)} stroke={g.color} />
                {/if}
            {/if}
        </svg>
        <div class="gauge-center">
            <div class="big-stat" class:muted={g.abstain} data-testid={g.testid}>
                {g.display}
            </div>
            {#if g.abstain}
                <div class="gauge-sub">insufficient signal</div>
            {:else if g.confidence}
                <div class="pip-row">
                    <span
                        class="pip"
                        class:conf-high={g.confidence === "high"}
                        class:conf-medium={g.confidence === "medium"}
                        class:conf-low={g.confidence === "low"}
                    ></span>
                    <span class="pip-label">{g.confidence}</span>
                </div>
            {/if}
        </div>
    </div>
{/snippet}

<div class="speedrun-dashboard">
    <h1>Speedrun dashboard</h1>

    <div class="cards">
        <!-- Memory score (or honest abstain) -->
        {#if view.kind === "abstain"}
            <div class="card score-card">
                <div class="card-title">Memory score</div>
                {@render gauge({
                    abstain: true,
                    display: "—",
                    valueT: 0,
                    lowT: 0,
                    highT: 0,
                    color: "",
                    confidence: null,
                    testid: "abstain",
                    label: "Memory score: insufficient signal, no score yet",
                })}
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
                {@render gauge({
                    abstain: false,
                    display: `${view.scorePct}%`,
                    valueT: view.scorePct / 100,
                    lowT: view.lowPct / 100,
                    highT: view.highPct / 100,
                    color: masteryColor(view.scorePct / 100),
                    confidence: view.confidence,
                    testid: "score",
                    label:
                        `Memory score ${view.scorePct} percent, 95% range ` +
                        `${view.lowPct} to ${view.highPct} percent, ` +
                        `${view.confidence} confidence`,
                })}
                <div class="range">
                    95% range: {view.lowPct}% – {view.highPct}%
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd
                        class="confidence"
                        class:conf-high={view.confidence === "high"}
                        class:conf-medium={view.confidence === "medium"}
                        class:conf-low={view.confidence === "low"}
                    >
                        {view.confidence}
                    </dd>
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
                {@render gauge({
                    abstain: true,
                    display: "—",
                    valueT: 0,
                    lowT: 0,
                    highT: 0,
                    color: "",
                    confidence: null,
                    testid: "performance-abstain",
                    label: "Performance: insufficient signal, no score yet",
                })}
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
                {@render gauge({
                    abstain: false,
                    display: `${view.performance.scorePct}%`,
                    valueT: view.performance.scorePct / 100,
                    lowT: view.performance.lowPct / 100,
                    highT: view.performance.highPct / 100,
                    color: masteryColor(view.performance.scorePct / 100),
                    confidence: view.performance.confidence,
                    testid: "performance-score",
                    label:
                        `Performance ${view.performance.scorePct} percent, 95% range ` +
                        `${view.performance.lowPct} to ${view.performance.highPct} ` +
                        `percent, ${view.performance.confidence} confidence`,
                })}
                <div class="range">
                    95% range: {view.performance.lowPct}% – {view.performance.highPct}%
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd
                        class="confidence"
                        class:conf-high={view.performance.confidence === "high"}
                        class:conf-medium={view.performance.confidence === "medium"}
                        class:conf-low={view.performance.confidence === "low"}
                    >
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
                {@render gauge({
                    abstain: true,
                    display: "—",
                    valueT: 0,
                    lowT: 0,
                    highT: 0,
                    color: "",
                    confidence: null,
                    testid: "readiness-abstain",
                    label: "Readiness: insufficient signal, no score yet",
                })}
                <p class="explain">Not enough evidence to project an exam score.</p>
                {#if view.readiness.reasons.length > 0}
                    <ul class="reasons">
                        {#each view.readiness.reasons as reason}
                            <li>{reason}</li>
                        {/each}
                    </ul>
                {/if}
            {:else}
                {@render gauge({
                    abstain: false,
                    display: `${view.readiness.score}`,
                    valueT: readinessT(view.readiness.score),
                    lowT: readinessT(view.readiness.low),
                    highT: readinessT(view.readiness.high),
                    color: masteryColor(readinessT(view.readiness.score)),
                    confidence: view.readiness.confidence,
                    testid: "readiness-score",
                    label:
                        `Readiness ${view.readiness.score} on the 200 to 990 scale, ` +
                        `range ${view.readiness.low} to ${view.readiness.high}, ` +
                        `${view.readiness.confidence} confidence`,
                })}
                <div class="range">
                    range: {view.readiness.low} – {view.readiness.high}
                </div>
                <dl class="meta">
                    <dt>Confidence</dt>
                    <dd
                        class="confidence"
                        class:conf-high={view.readiness.confidence === "high"}
                        class:conf-medium={view.readiness.confidence === "medium"}
                        class:conf-low={view.readiness.confidence === "low"}
                    >
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
                    <td class="num">
                        <div class="mbar" aria-hidden="true">
                            <div
                                class="mbar-fill"
                                style="width: {topic.meanRetrievabilityPct}%; background: {masteryColor(
                                    topic.meanRetrievabilityPct / 100,
                                )};"
                            ></div>
                        </div>
                        <span class="mbar-val">{topic.meanRetrievabilityPct}%</span>
                    </td>
                    <td class="num">{topic.medianLatencyMs} ms</td>
                </tr>
            {/each}
        </tbody>
    </table>
</div>

<style lang="scss">
    // Observatory accents, scoped to this component. Surfaces stay on Anki
    // design tokens (so the dashboard is clean in light and cosmic in dark);
    // the accents are used only for the arcs, pips and mastery emphasis.
    .speedrun-dashboard {
        --pg-accent: #4ce0ff;
        --pg-ok: #3dd68c;
        --pg-warn: #f5b14c;
        --pg-bad: #ff5c6c;
        --pg-mastery-0: #ff4c4c;
        --pg-mastery-50: #f5b14c;
        --pg-mastery-100: #3dd68c;
        // rgba variants (literals, not color-mix) so the arcs/pips glow softly
        // without hardcoding surface colors.
        --pg-accent-faint: rgba(76, 224, 255, 0.22);
        --pg-ok-glow: rgba(61, 214, 140, 0.6);
        --pg-warn-glow: rgba(245, 177, 76, 0.6);
        --pg-mono:
            ui-monospace, "SF Mono", "JetBrains Mono", "Cascadia Code", monospace;

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
        // A faint accent hairline at the top reads as cosmic in dark and stays
        // subtle in light — driven off the accent, not a full dark fill.
        box-shadow: inset 0 2px 0 -1px var(--pg-accent-faint);
    }

    // Mono eyebrow styling for the card title — Observatory character without
    // changing any title strings.
    .card-title {
        font-family: var(--pg-mono);
        font-size: 0.72em;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--fg-subtle, inherit);
        margin-bottom: 0.25em;
    }

    // ---- Gauge ring -----------------------------------------------------
    .gauge {
        position: relative;
        width: 100%;
        max-width: 12em;
        aspect-ratio: 1 / 1;
        margin: 0.35em auto 0.6em;
    }

    .gauge svg {
        display: block;
        width: 100%;
        height: 100%;
        overflow: visible;
    }

    .gauge .track {
        fill: none;
        stroke: var(--border);
        stroke-width: 8;
        stroke-linecap: round;
        opacity: 0.7;
    }

    // 95% Wilson uncertainty band: a fainter, wider arc behind the value arc.
    .gauge .band {
        fill: none;
        stroke-width: 14;
        stroke-linecap: round;
        opacity: 0.22;
    }

    .gauge .value {
        fill: none;
        stroke-width: 8;
        stroke-linecap: round;
    }

    .gauge.abstain .track {
        opacity: 0.4;
    }

    .gauge-center {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.2em;
        text-align: center;
    }

    .big-stat {
        font-size: 2.1em;
        font-weight: bold;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
        font-feature-settings: "tnum" 1;
    }

    .big-stat.muted {
        color: var(--fg-subtle, var(--fg-disabled));
        font-size: 2.1em;
    }

    .gauge-sub {
        font-family: var(--pg-mono);
        font-size: 0.6em;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--fg-subtle, inherit);
    }

    // ---- Confidence pip (styles the previously-unstyled .conf-* hooks) ---
    .pip-row {
        display: flex;
        align-items: center;
        gap: 0.4em;
        font-family: var(--pg-mono);
        font-size: 0.62em;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--fg-subtle, inherit);
    }

    .pip {
        width: 0.62em;
        height: 0.62em;
        border-radius: 50%;
        background: var(--fg-subtle, currentColor);
    }

    .conf-high {
        color: var(--pg-ok);
    }

    .conf-medium {
        color: var(--pg-warn);
    }

    .conf-low {
        color: var(--fg-subtle, inherit);
    }

    .pip.conf-high {
        background: var(--pg-ok);
        box-shadow: 0 0 6px var(--pg-ok-glow);
    }

    .pip.conf-medium {
        background: var(--pg-warn);
        box-shadow: 0 0 6px var(--pg-warn-glow);
    }

    .pip.conf-low {
        background: var(--fg-subtle, currentColor);
    }

    .range {
        margin-top: 0.25em;
        text-align: center;
        color: var(--fg-subtle, inherit);
    }

    .explain {
        font-size: 0.9em;
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
        font-variant-numeric: tabular-nums;
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
        font-variant-numeric: tabular-nums;
    }

    table.topics th {
        font-family: var(--pg-mono);
        font-size: 0.72em;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--fg-subtle, inherit);
    }

    table.topics .num {
        text-align: right;
    }

    // Per-subject mastery mini bar (red → amber → green ramp).
    .mbar {
        height: 0.35em;
        border-radius: 999px;
        background: var(--border);
        overflow: hidden;
        margin-bottom: 0.15em;
    }

    .mbar-fill {
        height: 100%;
        border-radius: 999px;
    }

    .mbar-val {
        font-size: 0.85em;
        color: var(--fg-subtle, inherit);
    }

    // Motion budget: one gentle draw-in on the gauge, only when the user has
    // not asked to reduce motion.
    @media (prefers-reduced-motion: no-preference) {
        .gauge .value {
            animation: gauge-draw 180ms ease-out both;
        }
    }

    @keyframes gauge-draw {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
</style>
