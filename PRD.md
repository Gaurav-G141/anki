# Speedrun PGRE — Product Requirements Document (Wednesday MVP)

> **Status:** Draft for review. This is the Wednesday-MVP PRD for _Speedrun_, an
> Anki fork targeting the **Physics GRE**. Edit freely — the **Open Assumptions**
> section (§11) lists every default I chose. A Wednesday task checklist is at the
> end (§13). Implementation has **not** started.

---

## 1. Context & Goal

We are forking Anki to build **Speedrun**, a desktop + iOS study app for **one
exam: the Physics GRE (PGRE)**. The project (per the Speedrun spec) is graded on
a _real_ Rust engine change, two apps sharing _one_ engine, three honestly-scored
signals (Memory / Performance / Readiness), reproducible held-out testing, and an
ablation-tested study feature — built in order (apps → AI → proof) across
Wed/Fri/Sun.

This PRD covers **only the Wednesday MVP** (no AI), but every architecture choice
is made so Friday (AI + two-way sync + 3 scores on phone) and Sunday (calibration,
performance model, score mapping, ablation, installers) slot in without rework.

**Wednesday headline (from the spec):** _Both apps work and review the same deck.
No AI._

**Why these choices (from the PGRE Brainlift):** the PGRE bottleneck is _execution
speed_, not knowledge (~1:43/question, no calculator). So the product optimizes
for rapid recall, heuristics, interleaving, and — our chosen study feature —
**speed-mode recall**, treating answer latency as a first-class measured signal.

---

## 2. Target Exam: Physics GRE

- **Format (post-Sept-2023):** 70 multiple-choice questions, 2 hours, no
  calculator, no wrong-answer penalty. Computer-based.
- **Scoring:** total scaled score **200–990**; ~60/70 correct ≈ 990. Three
  official **subscores**: (1) Classical Mechanics, (2) Electromagnetism,
  (3) Quantum Mechanics & Atomic Physics.
- **Content weights** (ETS standard — _verify against the ETS fact sheet before
  finalizing_): Classical Mechanics 20%, Electromagnetism 18%, Quantum Mechanics
  12%, Atomic Physics 10%, Thermodynamics & Statistical Mechanics 10%, Optics &
  Waves 9%, Specialized Topics 9%, Special Relativity 6%, Laboratory Methods 6%.
- **Readiness scale (for later):** project onto 200–990 with a range + confidence.
  Stated at the top of the README per spec §5.

---

## 3. Product Thesis (Brainlift → features)

| Brainlift insight                               | Product expression                                        | MVP?                                   |
| ----------------------------------------------- | --------------------------------------------------------- | -------------------------------------- |
| Speed > content; heuristics over breadth        | Latency is a tracked signal; speed-mode recall            | latency: yes; speed-mode UI: stretch   |
| Weight toward high-yield, lower-division topics | Topic taxonomy + per-topic weights drive coverage/mastery | yes (taxonomy + mastery query)         |
| Interleaving is non-negotiable                  | Mixed-topic review ordering                               | architecture only (full feature later) |
| Volume of problems is the core loop             | Review loop is the default screen                         | yes                                    |
| Generation effect (derive→reveal)               | Learning-card template style                              | later                                  |
| Review mistakes; test under real conditions     | Mistake review + timed test mode                          | later                                  |

Our **ablation study feature (spec §8)** = **speed-mode recall**: "Imposing a
per-card recall deadline (speed mode) improves answer latency on held-out
formula-recall cards at equal study time, without lowering accuracy." Tested
Sunday with three builds (feature on / off / plain Anki). Architecture must let
us toggle it and log latency from day one.

**Why speed-mode and not interleaving as the ablation feature** — even though the
Brainlift names interleaving more often than any other idea: speed-mode produces a
clean, already-instrumented dependent variable (`taken_millis`, §6.5) that is
straightforward to ablate at MVP deck scale, whereas a genuine interleaving
experiment requires a scheduler/queue change and a larger, multi-topic deck to
measure. We therefore _measure_ latency from day one and defer interleaving as a
built feature (§6.8), keeping the ablation tight and honest.

**On "derive, don't memorize":** the Brainlift holds this (Kahn/Anderson) alongside
"Memory and Speed > Understanding" and "only a select few hundred formulas are worth
memory." These are not in conflict — speed-mode recall targets exactly that select
core of memory-worthy formulas, while the derive-first _learning_ sections
(generation effect, below) carry the understanding half.

---

## 4. The Three Scores & The Honesty Rule

The spec's central trap: Memory ≠ Performance ≠ Readiness. We must show three
separate signals, each with a range, and **abstain when data is insufficient**.

This three-way split is the product's direct answer to the Brainlift's sharpest
cautionary finding: a student who read _Conquering_ cover-to-cover, drilled **Anki
flashcards daily** on a systematic 12-week plan, and took practice exams under real
conditions _still plateaued around 800_. Recall (Memory) demonstrably does **not**
equal exam Readiness — so collapsing them into one number would repeat the very
mistake the Brainlift warns against.

- **Memory** — chance the student recalls a taught fact. _(MVP: implemented,
  FSRS-derived.)_
- **Performance** — chance of answering a _new_ exam-style question right.
  _(Later: Friday/Sunday. MVP: schema + UI placeholder only.)_
- **Readiness** — projected 200–990 score with range + confidence. _(Later. MVP:
  schema + UI placeholder only.)_

**Honesty rule (enforced in MVP for the Memory score):** never show a score
without (a) the point estimate, (b) a likely range, (c) % topic coverage, (d) a
"how sure" indicator, (e) last-updated time, (f) the main reasons, (g) the
give-up rule. A bare number is an automatic fail.

**Give-up rule (MVP default — editable):** _Show no Memory score until the
collection has ≥ 100 graded reviews **and** ≥ 40% topic coverage._ (Spec example
was 200 reviews / 50% coverage; tune to deck size.) The abstain state is itself a
demo asset: import deck → dashboard shows "Not enough data yet, here's what's
missing" → after reviews, the score appears.

---

## 5. Scope — Wednesday MVP

**In scope (maps 1:1 to the spec's Wednesday checklist):**

_Desktop:_

- Anki fork building from source (already builds via `just run`).
- **One real Rust change end-to-end:** the **Mastery-query RPC** (§7) + ≥3 Rust
  unit tests + 1 Python test calling it.
- A review loop running on the **PGRE exam deck** (imported, topic-tagged).
- A **Memory model** with an honest score (range + give-up rule), shown on a new
  Svelte dashboard.
- A **desktop installer** that runs on a clean machine.

_iOS:_

- A SwiftUI app that **builds and runs on the iOS Simulator**, loads the PGRE
  deck, and runs a **real review session on the shared Rust engine** via a new
  C-FFI. _(Two-way sync NOT required Wednesday — reviewing the same deck is.)_

**Out of scope for Wednesday (designed-for, not built):** any AI (no model calls,
no generated cards, no chatbot); two-way sync; offline-sync; Performance &
Readiness scores; the ablation experiment; calibration charts; signing/TestFlight.

---

## 6. Architecture (the load-bearing decisions)

### 6.1 One engine, multiple FFI hosts

The Rust core (`rslib`) exposes a single command interface
`Backend::run_service_method(service: u32, method: u32, input: &[u8]) -> Result<Vec<u8>, Vec<u8>>`
(generated by [rslib/rust_interface.rs](rslib/rust_interface.rs), dispatched via
[rslib/src/services.rs](rslib/src/services.rs)). Today the **PyO3** host
([pylib/rsbridge/lib.rs](pylib/rsbridge/lib.rs)) wraps it for desktop. We add a
second host for iOS:

- **New crate** `mobile/anki-ffi/` with `crate-type = ["staticlib"]`, exposing
  `#[no_mangle] extern "C"` wrappers around `init_backend`,
  `run_service_method`, `run_db_command_bytes`, `open_collection`, and a
  `free_result`. Header generated with `cbindgen`.
- Cross-compile to `aarch64-apple-ios-sim` (simulator; device/account deferred),
  package as an `.xcframework`.
- Swift calls these and speaks the **same protobuf** via `swift-protobuf`
  generated from the same `proto/anki/*.proto` files (single source of truth).
- Threading: call off the main thread (tokio runtime is lazy; mirror rsbridge's
  GIL-release pattern). `BackendAnkidroidService` already in the tree confirms
  mobile was a design goal.

_This is the spec's "share the engine, don't rewrite it" requirement: desktop and
iOS run identical Rust scheduling/FSRS code; only the host differs._

### 6.2 The Rust change: Mastery-query RPC (isolated for clean upstream merges)

To keep our fork's diff small and mergeable (spec 7a asks for the upstream files
touched + merge difficulty), all additions live in **new files**, not edits to
core logic:

- New proto: `proto/anki/speedrun.proto` defining a `SpeedrunService`.
- New module: `rslib/src/speedrun/` (`mod.rs` + `service.rs`).
- Touch only two existing files to register: add `pub mod speedrun;` to
  [rslib/src/lib.rs](rslib/src/lib.rs) and the service to the generated dispatch.

The RPC returns per-topic mastery + an overall honest memory score. It is
**read-only** (composes `SearchBuilder::from_tag_name()` + `search_cards()` +
`Card.memory_state` + `FSRS::current_retrievability_seconds(...)`), so **undo and
collection integrity are trivially unaffected** — important for the spec's "prove
undo still works" requirement.

**Why in Rust, not Python (spec 7a one-pager):** the dashboard must summarize up
to 50,000 cards within the speed targets (first load p95 < 1s, refresh < 500ms).
Doing it in Python means N per-card RPC round-trips; one Rust query over the
collection with direct DB + FSRS access does it in a single pass. Reusing
[rslib/src/browser_table.rs](rslib/src/browser_table.rs)'s retrievability pattern.

### 6.3 Topic taxonomy & tagging

- Tag convention on notes: `pgre::<subject>` (e.g. `pgre::classical_mechanics`),
  optional `pgre::heuristic::<name>` for heuristic drills.
- A weight table (subject → exam weight from §2) lives in our `speedrun` module
  (a Rust `const`/static map for MVP; promote to deck config later).
- Coverage = fraction of taxonomy subjects with ≥1 card (weighted by exam weight).
- Imported public deck will be **re-tagged** into this taxonomy (a documented
  one-time step; a small mapping table).
- **Planned refinement (post-MVP):** the Brainlift names specific high-yield
  _subtopics_ (small oscillations / normal modes, Gauss's-law applications,
  selection rules, particle-in-a-box, partition function, …) and a _difficulty_
  axis (master AP-Physics-C-level fundamentals first). The MVP taxonomy is
  subject-level only; we reserve `pgre::<subject>::<subtopic>` and a difficulty
  tier (e.g. `pgre::level::lower_division`) so "weight toward high-yield" can later
  bite below the subject level without reworking the tag scheme.

### 6.4 Memory score computation (FSRS-derived, honest)

- Per card with `memory_state`: current retrievability `R` via
  `FSRS::current_retrievability_seconds(state, seconds_since_last_review, decay)`.
- **Per-topic:** total cards, cards-with-state, mastered count (`R ≥ 0.9`, the
  "mastered" threshold — editable), mean `R`, mean stability.
- **Overall Memory score:** coverage-weighted mean `R` across topics (point
  estimate). **Range:** report a band (MVP: interquartile or a binomial/Wilson
  interval on mastered-fraction; method documented). **Confidence:** tied to
  coverage + total reviews. **Reasons:** weakest topics by `R`.
- Subject to the give-up rule (§4).

### 6.5 Speed/latency as a first-class signal

`RevlogEntry.taken_millis` ([rslib/src/revlog/mod.rs](rslib/src/revlog/mod.rs))
already records answer latency. We surface it from Wednesday (per-topic median
latency on the dashboard) so the Sunday speed-mode ablation has data from day one.
**Speed mode** (a per-card recall deadline in the reviewer) is a Wednesday
_stretch_; required by Sunday.

### 6.6 Desktop UI

- New **SvelteKit page** `ts/routes/speedrun-dashboard/` served by the existing
  mediasrv/webview pattern (like `deck-options`/`graphs`), calling
  `SpeedrunService` through the generated `@generated/backend` over protobuf.
- Shows: overall Memory score (or abstain state), per-topic table (coverage,
  mastered, mean R, median latency), and **disabled/placeholder** Performance &
  Readiness cards (so the three-score layout exists from the start).

### 6.7 iOS app

- Minimal SwiftUI app: bundles a prebuilt PGRE collection (import the tagged deck
  on desktop → export `.colpkg` → ship in app bundle → import/open into app
  Documents on first launch via the `open_collection` flow).
- Review screen drives the **same `SchedulerService`** review RPCs
  (`get_queued_cards`/`answer_card`) through the C-FFI; grade buttons
  (Again/Hard/Good/Easy). No scores, no sync (Wednesday bar).

### 6.8 Forward-compatibility seams (so later work is additive)

- **Three-score abstraction:** a `ScoreCard { estimate, range, coverage,
  confidence, updated_at, reasons[], abstained }` shape reused for all three;
  MVP fills Memory, stubs the others.
- **AI seam:** card generation / paraphrase questions / readiness will be a
  separate service + provider adapter (Claude) behind a flag; the app must run
  with AI off (spec). Nothing in MVP calls a model.
- **Sync seam:** reuse Anki's existing sync (`SyncService`) for Friday's two-way
  sync; conflict rule documented later. MVP doesn't sync but doesn't preclude it.
- **Performance model:** consumes the same topic tags + revlog latency + held-out
  exam-style questions; the paraphrase test (spec 7d) lives here later.
- **Heuristic-drill / question-triage seam:** the Brainlift elevates heuristics
  (dimensional analysis, limiting cases, numeric estimation, common-sense
  elimination) and _question-judging/triage_ (spot-and-skip time-sinks, answer
  easy first) to the #1 exam differentiator. MVP captures only the
  `pgre::heuristic::<name>` tag (§6.3); post-MVP this becomes a real mode — a
  heuristic-drill card style and a triage/skip-trainer in the timed test mode —
  most likely AI-assisted (word-problem → applicable-heuristic, per the Brainlift).
  Reserved here so the Brainlift's top theme is on the roadmap, not absent.

---

## 7. The Rust Change — detailed spec (`SpeedrunService.TopicMastery`)

**Proto (`proto/anki/speedrun.proto`):**

```proto
service SpeedrunService {
  rpc TopicMastery(TopicMasteryRequest) returns (TopicMasteryResponse);
}
message TopicMasteryRequest { float mastered_threshold = 1; } // default 0.9
message TopicMasteryResponse {
  repeated TopicMastery topics = 1;
  float overall_memory_score = 2;
  float coverage = 3;
  uint32 total_reviews = 4;
  bool abstain = 5;            // give-up rule result
}
message TopicMastery {
  string tag = 1; uint32 total_cards = 2; uint32 cards_with_state = 3;
  uint32 mastered = 4; float mean_retrievability = 5;
  float mean_stability = 6; uint32 median_latency_ms = 7;
}
```

**Impl:** `rslib/src/speedrun/service.rs` implements the generated
`SpeedrunService` trait for `Collection`; logic in `rslib/src/speedrun/mod.rs`
reusing `search_cards`, `Card::memory_state`,
`FSRS::current_retrievability_seconds`, `card.seconds_since_last_review`, and
revlog `taken_millis`.

**Tests (spec 7a requires ≥3 Rust + 1 Python):**

1. Rust: empty/zero-card topic → zeroes, `abstain = true`.
2. Rust: cards with known `memory_state` → correct mastered count at threshold.
3. Rust: coverage + give-up rule boundary (just below / above thresholds).
4. Python: open a test collection, call `col._backend.topic_mastery(...)`, assert
   shape/values (the cross-language test).
   Plus: a note that undo is unaffected (read-only) and the upstream-files-touched
   list (`lib.rs`, dispatch registration) with "trivial merge" assessment.

---

## 8. Non-functional requirements (MVP-relevant subset)

- **Performance:** dashboard first load p95 < 1s, refresh p95 < 500ms (drives the
  Rust-side mastery query). Full `make bench` harness is Sunday; MVP just stays
  within budget on the imported deck.
- **License:** AGPL-3.0-or-later, credit Anki, exam stated at top of README.
- **Crash safety:** don't regress Anki's guarantees; our change is read-only.
- **AI off:** trivially satisfied (no AI in MVP).

---

## 9. Build / Run / Verification (how we demo Wednesday)

1. **Fork builds:** `just run` launches desktop; `just check` passes. Capture
   commit hash + clean-build recording.
2. **Rust change e2e:** `just test-rust` (the 3 unit tests) + the Python test
   (`just test-py` or targeted) green. Show the diff.
3. **Deck + review loop:** import the tagged PGRE `.colpkg`; run a review session
   on desktop.
4. **Memory score:** open the Speedrun dashboard → show abstain state on a fresh
   deck, do reviews, show the score with range + coverage + reasons + give-up rule.
5. **Installer:** build the desktop installer (existing `qt/installer` Briefcase
   path) and record installing/running on a clean machine.
6. **iOS:** build the C-FFI xcframework (`aarch64-apple-ios-sim`), run the SwiftUI
   app in the Simulator, load the deck, record a review session on the shared
   engine.

**Proof artifacts (spec):** commit hash + clean-build recording, test results,
clean-machine install recording, phone-review screen recording.

---

## 10. Risks & Mitigations

| Risk                                                                                                                                                                                                                                                                                                                               | Severity | Mitigation                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **iOS C-FFI + xcframework** is the first non-Python FFI in the tree; cross-compile + Swift bindings are fiddly                                                                                                                                                                                                                     | High     | Start it **first** (spec: "Get Anki Building First"). Target the **Simulator** only for Wednesday. Keep the FFI surface tiny (4 functions). **Documented fallback: Android/AnkiDroid**, which already runs rslib, if the xcframework can't be stood up in time. |
| **Xcode not yet installed**                                                                                                                                                                                                                                                                                                        | Med      | Install Xcode + `rustup target add aarch64-apple-ios-sim` as task #0 on the iOS track; budget the download time.                                                                                                                                                |
| Public PGRE deck quality / tagging                                                                                                                                                                                                                                                                                                 | Med      | Re-tag into our taxonomy; if no good deck exists, hand-author a small tagged seed deck (≥ enough for coverage demo).                                                                                                                                            |
| **Authentic post-2023 item scarcity** — Brainlift caveats: the _only_ format-current full-length exam is the single ETS Practice Book test; pre-2024 sources are format-inaccurate (100Q→70Q, online). Threatens both deck content and Friday/Sunday **held-out Performance** evaluation (too few real items → leakage / overfit). | Med      | Use formula-recall cards (format-agnostic) for the MVP Memory demo; reserve the one official post-2023 exam strictly as a held-out set, never for study; flag the small-n caveat in the Performance/Readiness scores via the same abstain rule (§4).            |
| Adding a new proto service shifts service indices for the C-FFI                                                                                                                                                                                                                                                                    | Low      | Regenerate Swift/host constants from the build; never hardcode indices.                                                                                                                                                                                         |
| Give-up thresholds vs small deck                                                                                                                                                                                                                                                                                                   | Low      | Thresholds are config; tune so the demo shows both abstain and live states.                                                                                                                                                                                     |

---

## 11. Open Assumptions to Confirm/Edit (defaults — change freely)

1. PRD file location = repo root `PRD.md`. (Move if you prefer `docs/`.)
2. Mastered threshold = `R ≥ 0.9`; give-up rule = ≥100 reviews & ≥40% coverage.
3. Content weights in §2 are the ETS-standard split — verify exact numbers against
   the ETS fact sheet (Brainlift only firmly cites CM 20% / E&M 18% / QM 12%).
4. Tag scheme `pgre::<subject>` and the 9-subject taxonomy.
5. iOS target = Simulator for Wednesday; device/TestFlight deferred.
6. Solo build, and this repo is your AGPL fork (push remote TBD).
7. The Memory-score "range" method (interquartile vs Wilson interval) — pick one.

---

## 12. How later deadlines slot in (no rework)

- **Friday (AI + sync + 3 scores on phone):** add the AI service + provider
  adapter (Claude) behind a flag with source-traceability + held-out eval +
  baseline comparison; turn on Anki's two-way sync; fill the Performance &
  Readiness `ScoreCard`s already stubbed in the dashboard and the iOS app.
- **Sunday (prove + ship):** memory calibration chart + Brier/log-loss on
  held-out reviews; performance accuracy on held-out exam-style questions; score
  mapping to 200–990 with a range; the **speed-mode ablation** (on/off/plain Anki,
  equal time) using the latency we logged from day one; `make bench`; signed
  installers + iOS device/TestFlight build; leakage check; AI-card gold-set check.
  _Held-out caveat (Brainlift):_ authentic post-2023 exam items are scarce (one
  official ETS test), so the Performance held-out set will be small — guard with the
  leakage check above and report Performance/Readiness with honest small-n ranges
  (or abstain, §4) rather than over-claiming from thin data.

---

## 13. Wednesday task checklist (ordered)

**Track 0 — unblock (do first, in parallel):**

- [ ] Confirm the fork builds: `just run` and `just check` green; record commit hash.
- [ ] Install Xcode + `rustup target add aarch64-apple-ios-sim aarch64-apple-ios`.
- [ ] Source a public PGRE deck; design the `pgre::<subject>` tag mapping.

**Track A — desktop Rust change + memory score:**

- [ ] Add `proto/anki/speedrun.proto` (`SpeedrunService.TopicMastery`).
- [ ] Create `rslib/src/speedrun/{mod.rs,service.rs}`; register in `lib.rs`/dispatch.
- [ ] Implement `TopicMastery` (reuse search + `memory_state` + FSRS retrievability + revlog latency).
- [ ] Write 3 Rust unit tests + 1 Python cross-language test; `just test-rust`/`test-py` green.
- [ ] Write the 7a one-pager (why Rust) + upstream-files-touched/merge note.

**Track B — desktop UI + deck:**

- [ ] Import + re-tag the PGRE deck; export a `.colpkg` for iOS.
- [ ] Build `ts/routes/speedrun-dashboard/` calling `SpeedrunService`.
- [ ] Render Memory score with range/coverage/confidence/reasons/last-updated + the abstain state; stub Performance/Readiness cards.
- [ ] Verify the review loop runs on the PGRE deck.

**Track C — iOS companion:**

- [ ] Create `mobile/anki-ffi/` staticlib crate (4 `extern "C"` fns) + cbindgen header.
- [ ] Cross-compile to `aarch64-apple-ios-sim`; package `.xcframework`.
- [ ] SwiftUI app: bundle the `.colpkg`, open the collection, run a review session via `SchedulerService` over the C-FFI (swift-protobuf).
- [ ] Confirm it runs in the Simulator on the shared engine.

**Track D — package + capture proof:**

- [ ] Build the desktop installer; record a clean-machine install + run.
- [ ] Record: clean build, test results, desktop review + dashboard, iOS review session.
- [ ] README: state exam (PGRE), AGPL-3.0-or-later + Anki credit, build instructions, architecture overview, Rust-change note, files-touched list.
