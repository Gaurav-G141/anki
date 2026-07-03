# Ankimatter Observatory — UI build contract (desktop Qt + iOS)

This is the **single source of truth** every builder/verifier subagent follows so the
two apps look like one product. Direction chosen: **A. Ankimatter Observatory** — a
cosmic-dark physics observatory. Refined per the owner's notes:

1. **Strategic color/motion.** The base is calm, dark, and quiet — an _art piece_, not a
   cartoon. Bright cyan/violet and any motion are **reserved for the one thing we want
   the user to focus on** (the active spike, the primary CTA, a just-answered choice, a
   live score). Everywhere else: hairlines, dim text, restraint. Motion is subtle and
   always gated behind `prefers-reduced-motion`.
2. **Physics everywhere, tastefully.** Users are physicists. Use real physics language
   and glyphs as quiet decoration: mono eyebrows (`QUANTUM MECHANICS · 12/18`), faint
   equation/operator watermarks (`ℏ ∮ ∇ ψ λ ∂`), constellation hairlines between
   mastered subjects. Never kitschy.
3. **Keep ALL functionality.** No feature removed or rewired. Every accessibility id,
   bridge command (`pycmd(...)`, `window.showCoach`, script message handlers), RPC, and
   nav path is preserved. This is a **visual** overhaul.
4. **Serious structural change, not a recolor.** Rework layout, hierarchy, and signature
   elements — not just swap hex values.
5. **No AI-generated sprites.** All cosmic backgrounds, starfields, glows, rings, and the
   manifold are **procedurally drawn in CSS/SVG/Canvas** — offline, no licensing, fully
   tunable. The only candidate for a crafted raster asset is the iOS app icon (flagged
   separately, optional).

---

## 0. Global decisions (apply to both apps)

- **Dark-first heroes, token-driven utility.** The three desktop "hero" web pages
  (manifold home, MCQ, Speed Recall) and the iOS review/MCQ/scores render **Observatory
  dark always** (full-bleed cosmic bg) regardless of OS light/dark — they read as a
  focused instrument. The **Memory/Scores dashboard** stays token-driven so it is clean
  in light mode and cosmic in dark (it lives in standard app chrome).
- **Type.** No bundled fonts (avoids build/licensing risk). Two stacks:
  - _Display / UI_: `system-ui, -apple-system, "Segoe UI", sans-serif`, with tight
    tracking (`letter-spacing: -0.01em`) and `font-feature-settings: "tnum" 1` for all
    numerals (scores, counts, timers use **tabular figures**).
  - _Physics mono_ (eyebrows, units, counts, choice labels): `ui-monospace, "SF Mono",
    "JetBrains Mono", "Cascadia Code", monospace`, uppercase, `letter-spacing: 0.14em`.
  - (Space Grotesk / Orbitron can be bundled later if more punch is wanted — deferred.)
- **Motion budget.** One ambient drift (≥90s loop, ≤3% travel) on the starfield; one
  bloom pulse on the single focal element; ≤180ms ease on state changes (reveal,
  correct/incorrect). All wrapped in `@media (prefers-reduced-motion: reduce) { … none }`.

---

## 1. Design tokens

### 1a. Desktop — `qt/aqt/data/web/css/pgre.scss` (NEW, auto-compiles → `css/pgre.css`)

Exposes CSS custom properties on `:root`. Injected into each hero page via
`stdHtml(..., css=["css/pgre.css"])`. Values:

```
--pg-space:        #07080D;   /* deepest background            */
--pg-space-2:      #0C1020;   /* gradient companion (top glow) */
--pg-panel:        rgba(18,21,32,0.72);   /* glass panel fill  */
--pg-panel-2:      rgba(24,28,42,0.92);   /* solid-ish panel   */
--pg-line:         rgba(150,170,220,0.16);/* hairline border   */
--pg-line-strong:  rgba(150,170,220,0.34);
--pg-text:         #EAF0FF;
--pg-text-dim:     rgba(234,240,255,0.62);
--pg-text-faint:   rgba(234,240,255,0.36);

--pg-accent:       #4CE0FF;   /* electric cyan — FOCUS ONLY    */
--pg-accent-2:     #8A7CFF;   /* violet — AI coaching / 2ndary */
--pg-accent-glow:  rgba(76,224,255,0.45);
--pg-violet-glow:  rgba(138,124,255,0.40);

--pg-ok:           #3DD68C;   /* aurora green (correct/mastered)*/
--pg-warn:         #F5B14C;   /* amber                          */
--pg-bad:          #FF5C6C;   /* warm red                       */
--pg-info:         #6AA8FF;   /* soft blue                      */

/* mastery emission ramp — matches the Python HSV faces */
--pg-mastery-0:    #FF4C4C;   /* unmastered (red)   ~hsv(0,.7,1) */
--pg-mastery-50:   #F5B14C;   /* mid (amber)                    */
--pg-mastery-100:  #3DD68C;   /* mastered (aurora green)        */

--pg-radius:       14px;
--pg-radius-sm:    10px;
--pg-pill:         999px;
--pg-shadow:       0 10px 34px rgba(0,0,0,0.55);
--pg-glow:         0 0 22px var(--pg-accent-glow);
--pg-glow-violet:  0 0 22px var(--pg-violet-glow);

--pg-font:  system-ui, -apple-system, "Segoe UI", sans-serif;
--pg-mono:  ui-monospace, "SF Mono", "JetBrains Mono", "Cascadia Code", monospace;
```

Also in `pgre.scss` (so pages just add classes, not inline styles):

- `.pg-observatory` — full-bleed cosmic background utility (see §2, Starfield).
- `.pg-eyebrow` — mono uppercase 0.14em tracking, `--pg-text-dim`.
- `.pg-panel` / `.pg-panel--glass` — glass card (blur, hairline border, radius, shadow).
- `.pg-ring` — SVG/conic mastery ring helper vars (`--pg-ring-pct`, `--pg-ring-color`).
- `.pg-btn`, `.pg-btn--primary` (cyan glow, focus only), `.pg-btn--ghost` (hairline).
- `.pg-choice`, `.pg-choice.correct`, `.pg-choice.wrong` (bloom in/dim).
- `.pg-badge` + verdict modifiers `--optimal/--valid/--over/--guess/--flaw`.
- `.pg-watermark` — faint physics-glyph/equation decoration.
- `.conf-high/.conf-medium/.conf-low` — confidence pip colors (ok/warn/dim) for the
  dashboard's currently-unstyled hooks.

**Python mastery constants** (`pgre.py:193-198`) stay the source of truth for the SVG
face fills; only align the CSS ramp above to them (do **not** change the Python unless a
screenshot shows a clash). The manifold `#fff` (L584) → `var(--pg-text)`; the blue/orange
rgba literals → `var(--pg-accent)` / `var(--pg-accent-2)` etc.

### 1b. iOS — `Sources/Theme.swift` (NEW) + `Resources/Assets.xcassets/AccentColor`

`enum Palette` with `Color` statics mirroring the desktop tokens (same names, `pg`
prefix dropped): `space`, `space2`, `panel`, `line`, `lineStrong`, `text`, `textDim`,
`textFaint`, `accent` (#4CE0FF), `accent2` (#8A7CFF), `ok`, `warn`, `bad`, `info`, plus
`mastery(_ p: Double) -> Color` interpolating the ramp. Each defined with explicit
light/dark via `Color(UIColor { trait in … })` so heroes stay dark and utility adapts.

Reusable pieces (SwiftUI):

- `ObservatoryBackground` — a `View` drawing the starfield (Canvas: fixed pseudo-random
  star field + top radial glow; ambient drift gated on reduce-motion). Placed behind
  `List`/screens with the list background cleared.
- `GaugeRing(value:range:color:label:confidence:)` — the score gauge (arc + Wilson band
  - confidence pip). Used by ScoresView; abstain → dim "insufficient signal" node.
- `MasteryRing(pct:)` — small ring for deck rows.
- `PillButton`, `CountChip(_:kind:)`, `Eyebrow(_:)` (mono uppercase), `GlassCard()`
  modifier, and shared `ErrorState`/`EmptyState`/`LoadingState` views.
- `Typography`: `Font` helpers `.pgDisplay`, `.pgBody`, `.pgMono` (monospaced), all with
  `.monospacedDigit()` where numeric.

`AccentColor` asset = #4CE0FF (both appearances). Wire into `project.yml` sources
(`Resources/Assets.xcassets`) and set `.tint(Palette.accent)` at `RootView`
(`SpeedrunApp.swift`).

### 1c. iOS shared web CSS — `Sources/SpeedrunWeb.swift` (NEW)

`enum SpeedrunWeb { static let baseCSS = "…" }` — the Observatory token block + shared
`:root`, `body` (dark cosmic bg, `--pg-text`), `mjx-container`, `hr`, `img`. Mirrors the
desktop `pgre.scss` tokens so a card looks identical on both platforms. `CardWebView`
(ReviewView) and `MCQWebView.page` both build `<style>baseCSS + own component CSS</style>`
and use one shared MathJax include line. Factor the transparent-WKWebView setup into a
shared helper if convenient.

---

## 2. Starfield (shared technique, offline)

CSS (desktop) / Canvas (iOS). Layer stack, back to front:

1. Base gradient: `radial-gradient(140% 90% at 50% -10%, var(--pg-space-2) 0%, var(--pg-space) 58%)`.
2. Star layer: many tiny 1–2px dots (CSS: two `::before/::after` with long `box-shadow`
   dot lists at 0.5–0.9 opacity; iOS: Canvas points from a fixed seed — no `Math.random`
   at runtime in workflow scripts, but app code may seed normally). ≤180 stars.
3. Optional faint nebula: one large low-opacity violet radial in a corner (≤0.06 alpha).
4. Ambient drift: translate the star layer ≤3% over ≥90s, `prefers-reduced-motion` off.

Keep it **dim**. The stars must never compete with content; they set mood only.

---

## 3. Per-screen target (what "serious change" means)

### Desktop

**Manifold home** (`pgre.py` `_MANIFOLD_BODY`/`_MANIFOLD_SCRIPT`; add `css=` in
`manifold.py:refresh`): full-bleed `.pg-observatory`. Header: mono eyebrow
`ANKIMATTER · CALABI–YAU` + the LaTeX subtitle in `--pg-text-dim`; a faint operator
watermark behind. Manifold centered with a soft **bloom** halo; spikes become luminous
nodes — dim by default, the **hovered/active** one lights cyan with a halo; draw faint
**constellation hairlines** between mastered (green) subjects. Center "⚛ Practice MCQs"
is the glowing cyan **core** (the one loud element). Bottom bar → translucent glass
(`ManifoldBottomBar`; the buttons keep their `pycmd` cmds and emoji). Preserve drag-rotate.

**MCQ** (`pgre_quiz.py` `_QUIZ_PAGE`): dark glass **console**. `#hdr` progress becomes a
thin cyan arc/meter + mono `Q n / N`; `#score` tabular. `#genPill` → `.pg-badge` cyan.
Statement in a `.pg-panel`. `.choice` → `.pg-choice` console rows with a mono letter
chip; on answer the correct choice **blooms** `--pg-ok`, wrong **dims** to `--pg-bad`.
`#frq` textarea styled as a console input. Coaching `.card#coach` gets a **violet edge
glow** (`--pg-accent-2`); `.card#fast` a cyan hairline. Verdict `.badge` uses the token
verdict palette. `#summary .big` in tabular display. Keep the `pycmd('grade:…')` bridge
and `window.showCoach`.

**Speed Recall** (`speedrecall.py` `_PAGE_HTML`; keep `css=["css/reviewer.css"]`, add
`"css/pgre.css"`): cosmic dark. `#sr-timer` becomes a **glowing ring/meter** that fills
as latency grows (cyan→amber→red per the drill's own thresholds — reuse existing rate
logic, do not change scheduling). Card on a `.pg-panel`. `.sr-grade` buttons share the
grade palette (Again `--pg-bad` / Hard `--pg-warn` / Good `--pg-ok` / Easy `--pg-info`).
Keep all `pycmd`/`eval` hooks and the `#sr-close` Esc affordance.

**Memory dashboard** (`ts/routes/speedrun-dashboard/SpeedrunDashboard.svelte`): three
**gauge rings** (Memory/Performance/Readiness) drawn in SVG with the **Wilson
uncertainty band as a fainter arc** and a confidence pip; a "last updated" line and a
tiny history sparkline if data allows. Style the `.conf-*` hooks. Abstain → a designed
"insufficient signal" empty state, not grey text. Token-driven (cosmic in dark, clean in
light). Keep the honesty guard and the per-subject `<table class="topics">`.
_(The dataviz skill is loaded when building these gauges for accessible, consistent
light/dark rendering.)_

### iOS

**Root** (`SpeedrunApp.swift`): `.tint(Palette.accent)`; `ObservatoryBackground` behind
the nav stack; large-title styling.

**Deck list** (`DeckListView.swift`): rows → **constellation cards** (`GlassCard`) each
with a `MasteryRing` and mono `CountChip`s (new = info, lrn = warn, rev = ok — keep the
data, restyle). "Performance" MCQ row becomes a prominent cyan hero row. Section headers
mono/dim. **Preserve every a11y id** (`deck_…`, `openMCQ`, `openMCQrow`, `scores`,
`addDeck`, sync ids, `import_…`, `unsyncedDot`, etc.).

**Review** (`ReviewView.swift`): card floats on the starfield in a `GlassCard`; reveal
transition ≤180ms; `gradeButtons` neon-outlined using `Rating.color` (retuned to the
token palette in `ReviewSession.swift`: again `bad`, hard `warn`, good `ok`, easy
`info`). Keep `showAnswer`, `grade_<label>`, `finished`, `error`, `cardWeb`,
`reviewedCount`, and `SPEEDRUN_AUTOREVEAL`.

**MCQ** (`MCQView.swift`): WebView uses `SpeedrunWeb.baseCSS` + Observatory component CSS
(mirrors desktop MCQ). Correct **blooms**, wrong **dims**; coaching card violet edge.
Verdict badge map keeps the same five verdicts, restyled to tokens. Nav title stays
`"Practice MCQs"`.

**Scores** (`ScoresView.swift`): three `GaugeRing`s (Memory/Performance %, Readiness
scaled) with the Wilson range drawn as a band and a confidence pip; abstain = dim node +
reasons. **Card titles must stay `Memory`/`Performance`/`Readiness`** and the
`…Score`/`…Abstain` ids must stay derivable. Subjects section restyled.

---

## 4. Files touched (disjoint sets → safe to parallelize per screen)

**Foundation (owner builds first, shared → not parallelized):**
`qt/aqt/data/web/css/pgre.scss` (all tokens + component classes);
iOS `Sources/Theme.swift`, `Sources/SpeedrunWeb.swift`,
`Resources/Assets.xcassets/AccentColor.colorset/Contents.json`, `project.yml` (asset
wiring), `Sources/SpeedrunApp.swift` (`.tint` + background).

**Desktop screens (one builder each):**
`qt/aqt/pgre.py` + `qt/aqt/manifold.py` (manifold home + bottom bar + add `css=`);
`qt/aqt/pgre_quiz.py` (MCQ); `qt/aqt/speedrecall.py` (Speed Recall);
`ts/routes/speedrun-dashboard/SpeedrunDashboard.svelte` (+`lib.ts` only if a view-model
field is needed for sparkline; avoid touching the honesty guard).

**iOS screens (one builder each):**
`Sources/DeckListView.swift`; `Sources/ReviewView.swift` (+`ReviewSession.swift`
Rating.color); `Sources/MCQView.swift`; `Sources/ScoresView.swift`.

## 5. Verification (subagents)

- Desktop: `just check` stays green (fmt the new SCSS via dprint/ruff/prettier). Launch
  `ANKI_BASE=/tmp/obs just run` and/or render each hero page's HTML with the compiled
  `pgre.css` via a Playwright harness (precedent: `speedrun/render_generated.mjs`);
  screenshot manifold, MCQ, Speed Recall, dashboard in light + dark.
- iOS: `xcodegen generate` → `xcodebuild build` (simulator) → boot sim → `xcrun simctl io
  booted screenshot` for deck list, review, MCQ (+coaching), scores (score + abstain),
  light + dark. Reuse `SPEEDRUN_AUTOREVEAL=1`.
- Regression: `xcodebuild test` (unit + the 3 UITests) must pass unchanged — a11y ids
  preserved. Desktop `just test` unaffected (styling-only).
- Deliverable per screen: before/after screenshot pair for sign-off.

## 6. Non-negotiables checklist (every builder confirms)

- [ ] No bridge command / RPC / a11y id / nav title / card-title string changed.
- [ ] Motion gated on `prefers-reduced-motion`; bright color reserved for the focal element.
- [ ] No external asset fetched (CSP/offline safe); everything procedural.
- [ ] `just check` (desktop) / `xcodebuild test` (iOS) green.
