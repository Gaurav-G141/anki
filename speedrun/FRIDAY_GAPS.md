# Friday check — status and remaining work (excluding the AI feature)

**Exam:** Physics GRE. **Scale:** 200–990, 10-point increments; three ETS subscores
(Classical, E&M, Quantum/Atomic).

> **Update:** Gaps 1 and 2 below are now **implemented** — Performance and Readiness
> models exist across proto/Rust/Python/TS with ranges + independent give-up rules,
> and the iOS app has a Scores screen showing all three. This file is retained as the
> record of the original verdict and the wiring points; see the "Status" column and
> the closing note for what changed.

## The Friday bar (minus AI)

Friday builds on Wednesday. The non-AI requirements are:

- **Wednesday foundation (must still hold):** fork builds from source; a real Rust
  engine change (diff + ≥3 Rust tests + 1 Python test); a review loop on the exam
  deck; a memory model with an honest score (range + give-up rule); a desktop
  installer; a phone app that builds/runs and reviews the shared deck.
- **Friday, non-AI:** two-way sync (no lost/double-counted reviews); offline review
  that syncs on reconnect; **the phone shows the three scores (memory, performance,
  readiness) with ranges and follows the give-up rule.**
- **Cannot-break rule #3:** _Show three separate scores, each with a range, not one
  blended number._

## Status summary

| Requirement                                | Status      | Notes                                                                                                                   |
| ------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------- |
| Fork builds; AGPL; Anki credited           | ✅          | `LICENSE`, root `README.md`; per-file headers intact                                                                    |
| Real Rust change (20% of grade)            | ✅          | `SpeedrunService.TopicMastery` in `rslib/src/speedrun/`; ~18 Rust tests, 6 Python tests; read-only/undo/integrity proof |
| Review loop on exam deck (desktop + phone) | ✅          | Desktop review UI; iOS `testTwentyReviews` XCUITest                                                                     |
| Memory model, honest (range + give-up)     | ✅          | Wilson 95% + abstain rule                                                                                               |
| Two apps, one engine + two-way sync        | ✅          | iOS C-FFI over `rslib`; USN sync; Rust merge test; NWPathMonitor auto-sync                                              |
| Desktop installer                          | ✅          | `.dmg` builds; `just check` passes                                                                                      |
| **Three scores, each with a range**        | ✅ (was ❌) | Memory + Performance + Readiness, each with range + independent abstain                                                 |
| **Phone shows the three scores**           | ✅ (was ❌) | `ScoresView` calls TopicMastery RPC, renders all three with ranges + give-up                                            |

## What is already solid — do NOT rebuild

- **Rust engine change.** `rslib/src/speedrun/mod.rs` `topic_mastery_report`: read-only
  scan of `tag:pgre::*` cards + revlog, per-topic mastery, coverage, Wilson 95% memory
  score, abstain rule. New proto service (`proto/anki/speedrun.proto`), Python wrapper
  (`pylib/anki/speedrun.py`). Tests: `rslib/src/speedrun/tests_correctness.rs` (incl.
  `rpc_is_read_only_and_preserves_integrity`, 100× calls + `check_database`),
  `pylib/tests/test_speedrun.py`. **This clears the "no real Rust change → 50% cap."**
- **Sync.** iOS `CollectionStore` calls SyncLogin/SyncCollection/FullUploadOrDownload
  through the same engine; `NWPathMonitor` + scenePhase auto-sync; self-hosted
  `anki-sync-server` in-tree; `rslib/src/sync/collection/tests.rs::revlogs_are_never_lost_or_double_counted`
  proves both directions + offline-both-sides merge (each revlog exactly once).
  **This clears the "no phone companion that syncs → 70% cap."**
  - _Caveats noted in `speedrun/SYNC.md`:_ the merge test inserts revlog rows directly
    rather than via `answer_card`; iOS auto-sync is foreground-only.

## Gap 1 — Performance and Readiness models (with ranges + give-up) — IMPLEMENTED

Only `memory_score` existed. Performance and Readiness now exist across
proto/Rust/Python/TS. These are **not** AI features — they are the doc's §9 Step 2
(performance) and Step 3 (score mapping / readiness), feeding the 20% "Score accuracy
and honest uncertainty" area (separate from the 15% AI section).

### Honesty constraints (enforced)

- Every score ships with a **range** and a **confidence**, and **abstains** when data
  is thin (per-score, mirroring the memory give-up rule).
- Readiness (projected 200–990) uses a **documented linear-anchor mapping**, a **wide**
  range at low coverage, and a capped confidence — never a confident point number.
- **Per-score independent abstain:** Performance can score from grade history even when
  Memory abstains for lack of FSRS state, and vice-versa.

### What each score means (documented, defensible)

- **Memory** — mastered fraction (current FSRS recall ≥ threshold) + Wilson 95% range.
- **Performance** — demonstrated recall accuracy on graded reviews (grade ≥ _Good_),
  aggregate + Wilson 95% range. This is accuracy on _reviewed_ material, **not** a
  held-out generalization guarantee (the AI paraphrase test — §7d — is the Sunday proof).
  Independent abstain: needs graded reviews + coverage, but **not** FSRS state.
- **Readiness** — projected PGRE scaled score in `[200, 990]` (10-pt increments), mapped
  from Performance with a linear anchor (`200 + accuracy·790`); the range is the
  Wilson-mapped band **widened by a coverage penalty** so low coverage → wide range and
  a confidence capped below "high". Derived from Performance (abstains when it does).

### Wiring points (as implemented)

- **Proto** — `proto/anki/speedrun.proto`: `TopicMasteryResponse` fields **13–26**
  (`performance_*`, `readiness_*`), `TopicMastery.accuracy` (field 10). Additive only.
- **Rust** — `rslib/src/speedrun/mod.rs`: per-subject `correct` captured in the existing
  revlog loop; performance/readiness computed alongside memory; all fields populated in a
  single response. New helpers: `wilson_95` (reused), `weakest_reasons_by_accuracy`,
  readiness mapping constants.
- **Desktop TS** — `ts/routes/speedrun-dashboard/lib.ts` exposes per-score sub-views with
  their own honesty guards; `SpeedrunDashboard.svelte` renders three real cards.
- **Codegen** — `.proto` changes picked up by `just check` (Rust prost, TS pb, Python pb2).

## Gap 2 — Three scores on the phone — IMPLEMENTED

`mobile/SpeedrunApp/Generated/anki/speedrun.pb.swift` is generated + committed;
`AnkiEngine` has `speedrun = 43` / `topicMastery = 0`; `CollectionStore.fetchMastery()`
calls the RPC on the serial queue; `Sources/ScoresView.swift` ports the honesty/abstain
logic from `lib.ts` and renders Memory + Performance + Readiness with ranges + give-up
messages; `DeckListView` has a toolbar `chart.bar` link to it. No Rust/FFI changes were
needed beyond Gap 1.

## Gap 3 — Proof artifact (clean-device install + sync round-trip)

Record: (a) `.dmg` clean-install + launch, and (b) the phone→desktop sync round-trip.
Build steps: `BUILD_INSTALLERS.md`. (Documentation task, not code.)

## Verification

- **Backend/models:** `just check`; `cargo test -p anki speedrun`;
  `pytest pylib/tests/test_speedrun.py` (incl. the moderate-progress "dummy account"
  test asserting all three scores with ranges). Scores abstain honestly on the
  empty/low-coverage fixtures.
- **Desktop dashboard:** `just run`, open the mastery dashboard — three real score cards
  with ranges + confidence; each abstains with reasons on a thin deck.
- **Phone:** build the iOS app (Simulator), open the Scores screen — all three scores
  with ranges + give-up message; sync and confirm numbers match desktop.
- **Perf guard:** `just bench` — the new scores share the single scan, so it stays O(scan).
