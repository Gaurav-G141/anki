# Speedrun PGRE — MVP Build Specs & Test Plan

Companion to [PRD.md](PRD.md). This breaks the Wednesday MVP into discrete,
independently-assignable **specs (S0–S9)**. Each spec is self-contained: what to
build, where, with what tech, how to make it fast+accurate, and **its own test
cases** (deliberately stricter than the Speedrun doc). Source docs:
`./Speedrun_ A Desktop + Mobile Study App Built on Anki.pdf` and
`./PGRE Brainlift (2).pdf`.

> **Status:** specs + test cases only. No app code has been written. Test cases
> may be implemented against the current (unmodified) tree to capture baselines
> — see §G6.

---

## §A — How an agent should use this doc (don't read everything)

Each spec lists **READ** (the only files/sections you need) and **IGNORE**
(explicitly out of scope so you don't wander). Rule of thumb:

- Read [PRD.md](PRD.md) §1–§4 once for context, then **only your spec's section**
  and its READ list.
- Do not read the whole `rslib/` tree. Do not read other specs' code areas.
- Shared files (`proto/anki/`, `rslib/src/lib.rs`, the generated dispatch) are
  **edit-serialized** (see §B) — coordinate, don't free-edit.
- When you need a Rust/Python/TS pattern, copy from the exemplar file named in
  your spec rather than searching.

---

## §B — Parallelization & dependency graph

Two long chains run in parallel (desktop-data and iOS); deck prep and packaging
flank them.

```
S0 build bring-up ──┬──► S2 Rust RPC ──┬─► S4 Python wrapper ─┐
   (desktop)        │   (+S3 scoring)  └─► S5 Svelte dashboard ┤─► S9 installer
                    │                                          │   + proof capture
S0' iOS toolchain ──┴──► S6 iOS C-FFI ───► S7 SwiftUI review ──┘
S1 deck prep (independent, start immediately) ──────────────────► feeds S5/S7
```

**Can run fully in parallel (different people/agents, no shared files):**

- S1 (deck prep) — independent from hour 0.
- S2/S3 (Rust RPC + scoring) **vs** S6 (iOS C-FFI) — different crates, no overlap.
- S5 dashboard _scaffolding_ (static layout + mocked data) and S7 SwiftUI
  _scaffolding_ (mocked card) can start before their backends land.

**Must be sequential (one-by-one), because of shared-file edits or hard deps:**

1. **S0 before everything that compiles/runs.** Get `just run` green first
   (Speedrun doc: "Get Anki Building First").
2. **All `proto/anki/` edits batched and serialized.** A proto change triggers
   full codegen (`just check`) and shifts service indices; never let two agents
   edit protos concurrently. Land `speedrun.proto` once, regenerate, then S4/S5
   consume it.
3. **`rslib/src/lib.rs` + generated dispatch registration**: single edit, by the
   S2 owner.
4. **S2 → S4 → S5** for the _real_ wiring (S5 mock→real swap happens after S2).
5. **S6 → S7** (SwiftUI needs the xcframework).

**Isolated new files (safe to create in parallel, no conflicts):**
`rslib/src/speedrun/`, `mobile/anki-ffi/`, `ts/routes/speedrun-dashboard/`,
fixtures under `rslib/src/speedrun/tests/` and a `speedrun/fixtures/` deck dir.

---

## §C — Tech stack & required languages (what the docs force)

| Layer         | Required language/tooling                                           | Why (doc requirement)                                               | Useful features to use                                                                                                                                  |
| ------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Engine change | **Rust** (edition 2021, toolchain 1.92)                             | Speedrun §2: "a real change inside Anki's Rust code."               | `prost` protobuf types; `snafu`/`AnkiError` for errors; `select_nth_unstable` for O(n) median; `f64` accumulators; iterator fusion; reuse `fsrs` crate. |
| IPC contract  | **Protocol Buffers** (`prost` + `protoc-gen-es`)                    | Anki's cross-language API; new RPC must be a proto.                 | One new `SpeedrunService`; keep messages flat.                                                                                                          |
| Library glue  | **Python ≥3.10** (pylib)                                            | Spec: "1 test that calls your change from Python."                  | `col._backend.<rpc>()`; thin wrapper in `pylib/anki/`.                                                                                                  |
| Desktop UI    | **TypeScript + Svelte 5 (runes) / SvelteKit**                       | Existing frontend; honesty-rule display.                            | `@generated/backend` async calls; runes (`$state`,`$derived`); D3 only if needed.                                                                       |
| iOS host      | **Rust `staticlib` + C ABI**, **Swift/SwiftUI**, **swift-protobuf** | Spec §3: run rslib via C FFI, "share the engine, don't rewrite it." | `#[no_mangle] extern "C"`, `cbindgen`, `xcframework`, `DispatchQueue.global` for off-main-thread calls.                                                 |
| Build/pkg     | `just`, `cargo`, Briefcase installer, `xcodebuild`                  | Spec: installer on clean machine; phone build runs.                 | existing `qt/installer`.                                                                                                                                |

**License (non-negotiable, Speedrun §2):** AGPL-3.0-or-later, credit Anki, state
exam (PGRE) at top of README.

---

## §D — Stricter-than-doc thresholds (quick reference)

We tighten every measurable bar so a marginal pass in testing is still a
comfortable pass in the demo.

| Metric                       | Speedrun doc              | **This project (stricter)**                                                                                           |
| ---------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Rust change tests            | ≥3 Rust + 1 Python        | **≥8 Rust unit + 2 Python + 1 perf + 1 undo-safety**                                                                  |
| Crash test                   | kill 20×, 0 corruption    | **kill 50× incl. mid-write, on the 50k deck, 0 corruption**                                                           |
| Button-press ack             | p95 < 50 ms               | **p95 < 35 ms, p99 < 50 ms**                                                                                          |
| Next card after grade        | p95 < 100 ms              | **p95 < 70 ms, p99 < 100 ms**                                                                                         |
| Dashboard first load         | p95 < 1 s                 | **p95 < 700 ms, p99 < 1 s**                                                                                           |
| Dashboard refresh            | p95 < 500 ms              | **p95 < 250 ms, p99 < 400 ms**                                                                                        |
| TopicMastery RPC alone (50k) | (n/a)                     | **p95 < 150 ms, p99 < 250 ms**                                                                                        |
| Cold start                   | desktop <5 s / phone <4 s | **desktop <4 s / sim <4 s**                                                                                           |
| iOS Wednesday review         | "a review session"        | **≥20 graded answers persisted + re-openable on desktop**                                                             |
| Score honesty                | show range etc.           | **all 7 honesty fields present or RPC returns `abstain`; UI cannot render a bare number (enforced by test)**          |
| Give-up rule                 | "set a line"              | **exact boundary tested both sides, per-condition + joint; abstain also if any subject with weight ≥10% has 0 cards** |
| Accuracy (memory)            | (Sunday)                  | **per-card R matches Anki browser value ≤1e-4; aggregate matches in-test golden ≤1e-4**                               |

---

## §E — Test report schema & feedback protocol (how the testing agent talks back)

The testing agent must return **structured, numeric** feedback — never just
"looks good." One JSON object per test, rolled up per spec.

```json
{
    "spec": "S2",
    "test_id": "S2-T03",
    "type": "accuracy",
    "status": "FAIL",
    "metric": {
        "name": "max_abs_err",
        "value": 3.2e-3,
        "unit": "R",
        "threshold": 1e-4,
        "comparator": "<="
    },
    "expected": "mean_R=0.8123",
    "actual": "mean_R=0.8155",
    "repro": "cargo test -p anki speedrun::tests::small_deck_accuracy",
    "note": "hoist FSRS::new out of loop changed rounding? check f64 accum"
}
```

Per-spec rollup + a gate color:

```json
{
    "spec": "S2",
    "passed": 11,
    "failed": 1,
    "blocking_failed": 1,
    "gate": "RED",
    "summary": "accuracy test S2-T03 off by 3.2e-3"
}
```

**Feedback type by test type (what number to report):**

- **Functional** → `PASS/FAIL` + the single failing assertion (expected vs actual).
- **Accuracy** → the **error number** (max abs / relative) vs tolerance + PASS/FAIL.
- **Performance** → a **p50/p95/p99 table** (ms) vs threshold + PASS/FAIL; never a
  single hand-picked number (Speedrun §7h).
- **Integration/E2E** → PASS/FAIL + artifact (screen recording / log path).
- **Regression guard** → PASS/FAIL of `just check` (must stay green).

**Gate rule:** any `blocking_failed > 0` ⇒ `RED` (coding agent must fix before
merge). Non-blocking (e.g., a perf p99 slightly over on a cold first run) ⇒
`YELLOW` with the number. All green ⇒ `GREEN`.

**Determinism (Speedrun: "someone else can re-run and get the same result"):**
every test uses a fixed seed and a fixture (see §F); the runner is a single
command per stack (`cargo test -p anki speedrun`, `just test-py -k speedrun`,
`yarn vitest run speedrun`, `just test-e2e`) and prints a deterministic report
with a process exit code.

---

## §F — Shared fixtures (build once, reuse across specs)

Defined in `rslib/src/speedrun/tests/fixtures.rs` (Rust) and mirrored as a
`.colpkg` under `speedrun/fixtures/` for Python/iOS. All use a constant RNG seed.

- **FIX-EMPTY** — empty FSRS-enabled collection (`Collection::new()`, set
  `BoolKey::Fsrs`). Expect `abstain=true`.
- **FIX-SMALL** — deterministic deck: 9 subjects, ~40 cards, each card given a
  **known** `memory_state` (set directly via `card.memory_state = Some(FsrsMemoryState{..}); col.storage.update_card(&card)`) and explicit `revlog` rows with hand-chosen `taken_millis`. Every aggregate is hand-computable.
- **FIX-50K** — 50,000 cards across 9 subjects, synthetic seeded `memory_state` +
  revlog. For perf only.
- **FIX-MISSING-HIGHWEIGHT** — covers all subjects **except** Classical Mechanics
  (weight 20%) despite large card count. Drives the "abstain on missing
  high-weight section" rule (Speedrun §7c spirit applied to the memory score).
- **FIX-NO-FSRS** — cards with `memory_state == None` (FSRS off / new cards) to
  test None-handling.

Reuse Anki's own builders (from `rslib/src/tests.rs`): `NoteAdder::basic(&mut col).fields(&[..]).deck(id).add(&mut col)`, `col.add_tags_to_notes(&[id], "pgre::classical_mechanics")`, and the `revlog(kind, days_ago)` helper from `rslib/src/scheduler/fsrs/params.rs::tests`.

---

# Specs

---

## S0 — Build & toolchain bring-up

**Goal:** the fork builds and runs on desktop; iOS toolchain ready. _Do this
first; it gates everything (Speedrun: "Get Anki Building First")._

- **Location / READ:** repo root, [CLAUDE.md](CLAUDE.md)/[AGENTS.md](AGENTS.md),
  [docs/development.md](docs/development.md), [justfile](justfile). **IGNORE:** all
  app logic.
- **Tech:** `just`, `cargo`, Xcode + `rustup target add aarch64-apple-ios-sim
  aarch64-apple-ios`.
- **Build:** confirm `just run` launches; `just check` green. Record commit hash.
  Install Xcode; add iOS Rust targets (budget the multi-GB download — start now).
- **Parallelization:** desktop (`just run`) and iOS toolchain installs run in
  parallel. Blocks S2/S5/S6/S7.

**Tests (S0):**

- **S0-T01 (regression baseline, blocking):** `just check` exits 0 on the
  unmodified tree. _Feedback:_ PASS/FAIL + failing target.
- **S0-T02:** `cargo build -p anki --release` succeeds; capture cold/incremental
  times. _Feedback:_ seconds.
- **S0-T03:** `rustc --print target-list | grep aarch64-apple-ios-sim` present;
  `cargo build -p <ffi-crate> --target aarch64-apple-ios-sim` placeholder builds
  (after S6 scaffolding). _Feedback:_ PASS/FAIL.
- **S0-T04 (cold start, stricter):** desktop launch to usable < **4 s** (p95 over
  5 launches). _Feedback:_ p50/p95.

---

## S1 — Topic taxonomy & PGRE deck prep

**Goal:** an exam deck whose notes are tagged into the PGRE taxonomy, plus a
`.colpkg` for iOS.

- **Location / READ:** create `speedrun/fixtures/` and a tagging script under
  `speedrun/tools/` (Python using `anki` lib). READ [PRD.md](PRD.md) §2,§6.3.
  **IGNORE:** rslib internals, UI.
- **Tech:** Python (the `anki` package), the imported public deck (`.apkg`).
- **Architecture/decisions:**
  - Tag convention: the **subject prefix** `pgre::<subject>` (9 subjects from
    PRD §2), plus three reserved-but-MVP-optional tag families (PRD §6.3):
    `pgre::<subject>::<subtopic>` (high-yield subtopics, e.g.
    `pgre::classical_mechanics::small_oscillations`), `pgre::level::<tier>`
    (difficulty axis, e.g. `pgre::level::lower_division`), and
    `pgre::heuristic::<name>`. Only the **subject prefix** is required for the MVP;
    the others are reserved so the scheme doesn't change later.
  - The `pgre::heuristic::<name>` tag is the **seam** for the post-MVP
    heuristic-drill / question-triage mode (PRD §6.8) — tag now, build later; not
    in the MVP.
  - A canonical weight table (subject → exam weight) — single source, later read
    by S2. For MVP keep weights in S2's Rust module; S1 only assigns tags.
  - Every note maps to **exactly one subject prefix** `pgre::<subject>` (optionally
    carrying a `::<subtopic>` suffix), so mastery aggregation stays over disjoint
    subjects; `pgre::level::*` and `pgre::heuristic::*` are **not** subject tags and
    don't affect this rule (document it).
  - **Deck currency & held-out separation (PRD §10/§12):** prefer a
    format-current (post-Sept-2023) deck; pre-2024 sources are format-inaccurate.
    Reserve the single official post-2023 ETS practice exam **strictly as a
    held-out set — never import it for study** — to protect the later
    Performance/Readiness evaluation from leakage.
- **Parallelization:** fully independent — start at hour 0.

**Tests (S1):**

- **S1-T01:** 100% of notes carry exactly one `pgre::<subject>` **subject prefix**
  (no untagged, no double-subject); a `::<subtopic>` suffix still counts as its one
  subject, and `pgre::level::*` / `pgre::heuristic::*` tags are ignored by this
  check. _Feedback:_ count of violations (must be 0).
- **S1-T02:** all 9 subjects present (so coverage can reach 100%); report
  per-subject card counts. _Feedback:_ table.
- **S1-T03:** `.colpkg` re-imports cleanly into a fresh collection and
  `just check`-style integrity check (`Collection` opens, `dbcheck` clean).
  _Feedback:_ PASS/FAIL.
- **S1-T04 (stricter):** a deliberately-broken variant (one subject removed)
  exists as **FIX-MISSING-HIGHWEIGHT** for S2/S3 abstain tests.

---

## S2 — Rust engine change: `SpeedrunService.TopicMastery` RPC

**Goal:** the one real Rust change — a fast, read-only per-topic mastery +
memory-score query. (Speedrun §7a "Mastery query," stricter.)

- **Location / READ:** create `proto/anki/speedrun.proto`,
  `rslib/src/speedrun/{mod.rs,service.rs,tests/}`; register in
  `rslib/src/lib.rs`. **READ exemplars only:**
  `rslib/src/scheduler/fsrs/memory_state.rs:360–400` (`compute_memory_state`
  service shape), `rslib/src/browser_table.rs:541–556` (retrievability call),
  `rslib/src/search/builder.rs` (`from_tag_name`), `rslib/src/tests.rs` (builders),
  [docs/data-flow.md](docs/data-flow.md) (RPC dispatch), [docs/protobuf.md](docs/protobuf.md).
  **IGNORE:** scheduler answering internals, sync, UI, media.
- **Tech & features:** `prost`; `snafu`/`AnkiError`; the `fsrs` crate
  (`current_retrievability_seconds(state, seconds, decay)`); `select_nth_unstable`
  for median; `f64` accumulators → emit `f32`.
- **Architecture / data structures / algorithms (fast + accurate):**
  - **Single scan, no per-card RPC.** One prepared SQL statement joining
    `cards`→`notes` to stream `(memory_state, last_review_time, interval, due,
    decay, ctype, tags)`; map tag → `SubjectId` (a fixed `enum`, matched via a
    small `phf`/`match`, **not** a `HashMap`). Match on the **subject segment /
    prefix** `pgre::<subject>`, tolerating an optional `::<subtopic>` suffix, and
    **ignore** `pgre::level::*` and `pgre::heuristic::*` — so the reserved subtopic
    and difficulty tags (PRD §6.3) never break or double-count mapping.
  - Accumulate into a **fixed `[SubjectAccum; 9]` array** (cache-friendly), each:
    `total, with_state, mastered, sum_r: f64, sum_stab: f64`.
  - **Hoist `FSRS::new(None)` out of the loop** (the browser code constructs it
    per-row — do not copy that; construct once).
  - Retrievability per card via `current_retrievability_seconds` using
    `card.seconds_since_last_review(&timing)` and
    `card.decay.unwrap_or(FSRS5_DEFAULT_DECAY)`; `memory_state == None` ⇒ excluded
    from `with_state`/`sum_r` but still counted in `total` (None-handling is a
    tested case).
  - **Median latency:** second streamed query over `revlog`⋈`cards`⋈`notes`
    filtered to `review_kind ∈ {Learning,Review,Relearning}` and `taken_millis>0`,
    capped at 60 000 ms; collect per-subject `Vec<u32>`, median via
    `select_nth_unstable`. Note t-digest as a scale option (not MVP).
  - **Coverage** = Σ weight(subject with ≥1 card) (weights sum to 1.0).
  - **Overall memory score** = coverage-weighted mean of per-subject mean-R.
  - **Range** (pick one in PRD §11; default **Wilson** on mastered-fraction at
    95%): report `[low, high]`. **Confidence** = f(total_reviews, coverage).
  - **Abstain** = `total_reviews < REVIEW_MIN(100)` ∨ `coverage < COV_MIN(0.40)`
    ∨ any subject with weight ≥ 0.10 has 0 cards. Thresholds are `const`s.
  - Complexity O(C + R), memory O(R) for latency vectors.
- **Parallelization:** independent of S6. **Serialize** the proto edit + lib.rs
  registration. S4/S5 depend on this landing.

**Tests (S2) — ≥8 Rust unit, 1 perf, 1 undo-safety (stricter):**

- **S2-T01 functional (FIX-EMPTY):** `abstain=true`, all topic stats zero.
- **S2-T02 functional (FIX-SMALL):** topic counts (`total`, `with_state`,
  `mastered`) match hand counts exactly at threshold `R≥0.9`. Include at least one
  card tagged with a `::<subtopic>` suffix and one extra `pgre::level::*` /
  `pgre::heuristic::*` tag, and assert it maps to the correct subject without
  double-counting (prefix-matching per PRD §6.3).
- **S2-T03 accuracy (FIX-SMALL):** `mean_retrievability`, `overall_memory_score`,
  `coverage` equal an **in-test golden** (test independently calls
  `current_retrievability_seconds` per fixture card and aggregates). _Feedback:_
  `max_abs_err` (threshold ≤1e-4).
- **S2-T04 accuracy:** per-card R equals the value Anki's browser would show for
  the same card (reuse same fn) ≤1e-4.
- **S2-T05 median:** `median_latency_ms` per subject equals hand-computed median
  of the fixture's `taken_millis` (odd & even counts; cap applied).
- **S2-T06 None-handling (FIX-NO-FSRS):** cards with `memory_state==None` counted
  in `total`, excluded from `with_state`/score; no panic, no NaN.
- **S2-T07 give-up boundary:** at exactly `REVIEW_MIN-1` → abstain; at
  `REVIEW_MIN` with `coverage≥COV_MIN` → score present. Test each condition alone
  and jointly.
- **S2-T08 missing-high-weight (FIX-MISSING-HIGHWEIGHT):** abstain=true even with
  large card count (Classical Mechanics 20% absent).
- **S2-T09 determinism:** two calls on the same unchanged collection return
  byte-identical responses.
- **S2-T10 perf (FIX-50K, blocking):** RPC p95 < **150 ms**, p99 < **250 ms** over
  30 runs (warm). _Feedback:_ p50/p95/p99 table. (Run via `cargo bench --features
  bench` harness in `rslib/benches/`.)
- **S2-T11 undo-safety (regression, blocking):** snapshot `col` undo status +
  `dbcheck` before; call RPC 100×; assert undo stack unchanged, no DB
  mutation, `dbcheck` clean (read-only proof for Speedrun §7a).
- **S2-T12 Python cross-language (required by spec):** open FIX-SMALL `.colpkg`
  in Python, call `col._backend.topic_mastery(...)`, assert response matches the
  Rust golden (happy path) **and** FIX-EMPTY returns `abstain` (2 Python tests).
- **Regression guard:** `just check` stays green; existing tests unchanged.

---

## S3 — Memory score model (math correctness & honesty)

_Lives inside S2's module but tested separately because accuracy + the honesty
contract are graded heavily (Speedrun §4, §9 Step 1)._ Owner can be same as S2.

_Why the scores stay separate (PRD §4):_ the three-score split (Memory ≠
Performance ≠ Readiness) is the PRD's direct answer to the Brainlift finding that a
student who drilled Anki daily on a 12-week plan still plateaued ~800 — recall does
not equal exam readiness, so this spec must never collapse them into one number.

- **Location / READ:** the scoring functions in `rslib/src/speedrun/mod.rs`.
  **IGNORE:** SQL/scan plumbing (that's S2).
- **Architecture:** pure functions `fn memory_score(per_topic, weights) ->
  ScoreCard` and `fn confidence(reviews, coverage) -> Confidence`, unit-testable
  without a collection. `ScoreCard { estimate, low, high, coverage, confidence,
  updated_at, reasons[], abstained }` — the shared 3-score shape (PRD §6.8).
- **Parallelization:** can be written/tested against pure inputs in parallel with
  S2's plumbing; integrate when S2 lands.

**Tests (S3) — accuracy + property:**

- **S3-T01:** Wilson (or chosen) interval matches a reference implementation to
  ≤1e-6 on hand inputs; `low ≤ estimate ≤ high`; clamped to [0,1].
- **S3-T02 property (fuzz, seeded):** over 10k random valid inputs, never NaN/inf,
  `low≤high`, monotonic widening as n shrinks. _Feedback:_ #violations (0).
- **S3-T03 honesty contract:** when not abstaining, all 7 fields are populated
  (estimate, range, coverage, confidence, updated_at, ≥1 reason, give-up rule
  echoed); when abstaining, `estimate` is absent. _Feedback:_ PASS/FAIL list.
- **S3-T04 reasons:** `reasons` lists the lowest-R subjects in ascending order;
  matches hand expectation on FIX-SMALL.

---

## S4 — Python wrapper

**Goal:** a clean `pylib/anki` helper so callers don't touch `_backend`
(consistent with [docs/language_bridge.md](docs/language_bridge.md)).

- **Location / READ:** add a small module/method under `pylib/anki/` (e.g.
  `pylib/anki/speedrun.py` or a method on `Collection`). **READ:**
  `pylib/anki/decks.py:166–168` (wrapper pattern), `pylib/tests/shared.py`
  (`getEmptyCol`). **IGNORE:** UI, Rust internals.
- **Tech:** Python; generated `col._backend.topic_mastery(...)`.
- **Parallelization:** after S2 proto lands (codegen). Small.

**Tests (S4):**

- **S4-T01:** `getEmptyCol()` → wrapper returns an abstaining result object;
  typed fields accessible. PASS/FAIL.
- **S4-T02:** on FIX-SMALL, wrapper values equal the Rust golden (shared fixture).
- **S4-T03:** mypy/ruff clean (`just lint`). PASS/FAIL.

---

## S5 — Desktop Svelte dashboard

**Goal:** a SvelteKit page that renders the Memory score honestly (or the abstain
state) + per-topic table + disabled Performance/Readiness placeholders.

- **Location / READ:** `ts/routes/speedrun-dashboard/`. **READ exemplars:**
  `ts/routes/deck-options/` (page+lib+RPC call pattern), `ts/routes/graphs/`
  (data viz), `ts/lib/generated/post.ts` (transport), [docs/data-flow.md](docs/data-flow.md)
  §"TS → Rust path". **IGNORE:** Rust, iOS, scheduler.
- **Tech & features:** Svelte 5 runes (`$state`,`$derived`), TS,
  `import { topicMastery } from "@generated/backend"`, Sass; mediasrv/webview page
  registration like `deck-options`.
- **Architecture/decisions:**
  - A pure `lib.ts` state module (testable in vitest without a backend) that maps
    the proto response → view model; the `.svelte` file is thin.
  - **Honesty enforced in code:** the score component refuses to render a number
    unless all 7 fields are present; otherwise renders the abstain card with
    "what's missing." (Tested.)
  - Build the 3-score layout now (Performance/Readiness disabled) so later work is
    additive (PRD §6.8).
  - Scaffold with mocked data first (parallel with S2), swap to real RPC after S2.
- **Parallelization:** scaffolding parallel; real wiring after S2/S4.

**Tests (S5):**

- **S5-T01 vitest (pure logic):** mapping fn turns a sample proto (abstain) into
  the abstain view model; turns a populated proto into a score view model with
  all fields. _Feedback:_ PASS/FAIL per assertion.
- **S5-T02 vitest honesty guard (stricter):** given a proto missing any honesty
  field, the mapper/score-guard throws or returns abstain — it must be
  _impossible_ to render a bare number. _Feedback:_ PASS/FAIL.
- **S5-T03 e2e (Playwright):** navigate to `/speedrun-dashboard`, page mounts,
  shows abstain state on FIX-EMPTY profile; after seeded reviews, shows score +
  range + coverage + reasons. _Feedback:_ PASS/FAIL + screenshot.
- **S5-T04 perf (stricter):** dashboard first load p95 < **700 ms**, refresh p95 <
  **250 ms** on FIX-50K (measured in-page, RPC + render). _Feedback:_ p50/p95/p99.
- **S5-T05:** `just lint` (svelte-check + tsc) clean.

---

## S6 — iOS C-FFI crate (shared engine)

**Goal:** the first non-Python host for rslib — a tiny C ABI around the existing
command interface, packaged as an xcframework. (Speedrun §3.)

- **Location / READ:** new crate `mobile/anki-ffi/` (+ a build script
  `mobile/build-xcframework.sh`). **READ exemplar:** `pylib/rsbridge/lib.rs`
  (mirror its `command`/`run_service_method` wrapping), `rslib/src/backend/mod.rs`
  (`init_backend`, `run_service_method`, `run_db_command_bytes`),
  `rslib/src/backend/collection.rs` (`open_collection`),
  [docs/data-flow.md](docs/data-flow.md). **IGNORE:** PyO3 details, UI, scoring.
- **Tech & features:** `crate-type=["staticlib"]`; `#[no_mangle] extern "C"`;
  `cbindgen` for the header; `cargo build --target aarch64-apple-ios-sim`;
  `xcodebuild -create-xcframework`. Mirror rsbridge's GIL-release intent: the
  tokio runtime is lazy and calls block, so document "call off the main thread."
- **Architecture / FFI contract (4 functions, keep it tiny):**
  - `anki_open_backend(init_ptr,len) -> *mut Backend` (decode `BackendInit`).
  - `anki_command(be, service:u32, method:u32, in_ptr, in_len, out_len*,
    status*) -> *mut u8` — returns an owned buffer; `status` distinguishes Ok vs
    a `BackendError`-proto payload. (Mirror `run_service_method`'s
    `Result<Vec<u8>,Vec<u8>>`.)
  - `anki_free(ptr,len)` — Rust owns/frees all returned buffers (document
    ownership; use `Vec::into_raw_parts`/reconstruct).
  - `anki_close_backend(be)`.
  - `open_collection` is just a `command` call (CollectionService) — no special fn
    needed beyond passing the path-based request.
  - **Don't** wire this into `ninja_gen` for MVP — standalone cargo + script.
- **Parallelization:** independent of S2 (separate crate). Blocks S7.

**Tests (S6):**

- **S6-T01 build:** `cargo build -p anki-ffi --target aarch64-apple-ios-sim
  --release` succeeds; cbindgen header generated; xcframework assembles.
  _Feedback:_ PASS/FAIL + artifact path.
- **S6-T02 round-trip (host unit test, x86/arm mac):** from Rust/C test, open an
  in-memory backend, call a trivial RPC (e.g. i18n/version) via `anki_command`,
  decode the protobuf response. _Feedback:_ PASS/FAIL.
- **S6-T03 memory safety (stricter):** run the round-trip 10k× under
  AddressSanitizer / leak check; 0 leaks, 0 invalid frees. _Feedback:_ leak count.
- **S6-T04 engine-parity:** `buildhash()` from the FFI equals the desktop
  build's (proves same engine, not a fork). _Feedback:_ PASS/FAIL.
- **S6-T05 open+query:** `anki_command(open_collection)` on the FIX-SMALL `.anki2`,
  then `topic_mastery` — response equals the desktop Rust golden. _Feedback:_
  max_abs_err.

---

## S7 — iOS SwiftUI review app

**Goal:** a minimal app that, in the Simulator, opens the PGRE deck and runs a
real review session on the shared engine. (Wednesday bar; no sync, no scores.)

- **Location / READ:** new Xcode project `mobile/SpeedrunApp/`. **READ:** S6's
  generated header + `proto/anki/scheduler.proto` (`GetQueuedCards`,
  `CardAnswer`/`AnswerCard`), the scheduler RPC report (get_queued_cards /
  answer_card fields). **IGNORE:** desktop UI, scoring, Rust internals.
- **Tech & features:** SwiftUI; `swift-protobuf` generated from `proto/anki/*`;
  call the C FFI off-main-thread (`DispatchQueue.global`); bundle a prebuilt
  `.anki2`(+`.media`) copied to `Documents` on first launch, then `open_collection`.
- **Architecture/decisions:**
  - Review loop: `get_queued_cards(fetch_limit)` → render front → reveal back →
    grade → build `CardAnswer{card_id, current_state, new_state (from QueuedCard.states),
    rating, answered_at_millis=now, milliseconds_taken=measured}` → `answer_card`.
  - **Capture latency client-side** (`CACurrentMediaTime` delta) — this is the
    speed signal the Sunday ablation needs; persist via the normal answer path
    (`taken_millis`).
  - Keep all engine state in Rust; Swift holds only view state.
- **Parallelization:** UI scaffolding (mocked card) parallel with S6; real wiring
  after S6.

**Tests (S7):**

- **S7-T01 build/run:** app builds and launches in the iOS Simulator; opens the
  deck. _Feedback:_ PASS/FAIL + recording.
- **S7-T02 review session (stricter):** complete **≥20** graded answers; assert 20
  `revlog` rows persisted with nonzero `taken_millis`. _Feedback:_ count.
- **S7-T03 engine-shared proof:** after the session, open the same `.anki2` on
  desktop Anki → the 20 cards show updated due/interval/state (manual,
  recorded; no sync required Wednesday). _Feedback:_ PASS/FAIL + recording.
- **S7-T04 latency capture:** recorded `taken_millis` are within ±10% of a
  stopwatch on 3 sampled cards. _Feedback:_ %error.
- **S7-T05 cold start (stricter):** sim cold start < **4 s** (p95/5 launches).

---

## S8 — Speed-mode signal surfacing (light, Wednesday-optional)

**Goal:** surface per-topic median latency on the dashboard now so the Sunday
speed-mode ablation has data. _Full speed-mode UI (per-card deadline) is Sunday._

_Why speed-mode is the ablation signal (PRD §3):_ latency (`taken_millis`) is an
already-instrumented, cleanly-ablatable dependent variable at MVP deck scale,
whereas a real interleaving experiment needs a scheduler/queue change and a larger
multi-topic deck. So the MVP **measures** latency from day one and defers
interleaving as a built feature (PRD §6.8) — keeping the ablation tight and honest.

- **Location:** `median_latency_ms` already produced by S2; S5 renders it.
  **IGNORE:** the ablation harness (Sunday).
- **Tests (S8):** **S8-T01** dashboard shows per-topic median latency matching the
  S2 value on FIX-SMALL. PASS/FAIL.

---

## S9 — Desktop installer + proof capture

**Goal:** an installer that runs on a clean machine + the Speedrun proof bundle.

- **Location / READ:** [qt/installer/](qt/installer/), [docs/releasing.md](docs/releasing.md).
  **IGNORE:** app logic.
- **Tech:** existing Briefcase installer + `just` wheel/build recipes.
- **Parallelization:** validate the unmodified installer early (regression
  baseline), re-run at the end after features land.

**Tests (S9):**

- **S9-T01 (stricter):** install on a **clean** VM/user account (no dev deps);
  app launches, opens the deck, dashboard renders. _Feedback:_ PASS/FAIL +
  clean-machine recording.
- **S9-T02 crash/corruption (stricter):** kill the app **50×** (incl. mid-write)
  while reviewing the **50k** deck; afterwards `dbcheck` clean every time, 0
  corrupted collections. _Feedback:_ corruption count (must be 0).
- **S9-T03 proof bundle complete:** commit hash + clean-build recording + test
  report + clean-install recording + iOS review recording all present
  (Speedrun "Due Wednesday → Proof"). _Feedback:_ checklist.

---

## §G — Global testing notes

- **G1 Regression guard (always):** `just check` must stay green after every spec;
  our additions live in new files, so existing test outputs must not change.
- **G2 Order of testing:** run S0 baselines first (green tree + perf baselines),
  then per-spec gates, then S9 integration last.
- **G3 Blocking vs non-blocking:** perf p99 marginal = YELLOW; any accuracy,
  correctness, undo-safety, corruption, or honesty failure = RED (must fix).
- **G4 Where numbers come from:** accuracy goldens are computed _in the test_ from
  the same `fsrs` fn (version-proof); perf from the criterion/in-page harness over
  ≥30 warm runs reporting p50/p95/p99.
- **G5 Stricter rationale:** every threshold in §D is tightened ~1.5–2× vs the doc
  so a CI pass survives a noisy live demo machine.
- **G6 Baseline capture (offered):** the testing agent can run §S0-T01/T02/T04 and
  review-loop perf on the **current unmodified tree** now to record baselines and
  confirm the harness works; the new-feature tests (S2–S8) will fail until built
  (expected RED → turns GREEN as specs land). I have **not** run these yet — say
  the word and I'll capture the baseline pass.
