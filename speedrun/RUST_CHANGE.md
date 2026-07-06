# The Rust engine change (Speedrun §7a)

_Last updated: 2026-07-05._

**Change:** a new read-only backend RPC, `SpeedrunService.TopicMastery`
([proto/anki/speedrun.proto](../proto/anki/speedrun.proto),
[rslib/src/speedrun/](../rslib/src/speedrun/)). It scans the PGRE-tagged
collection and returns per-topic mastery (cards, cards-with-FSRS-state, mastered
count, mean retrievability, mean stability, median answer latency) plus an
honest, range-bearing memory score (mastered fraction + Wilson 95% interval) or
an abstaining result when there isn't enough data. This is the "mastery query"
option from §7a.

## Why this belongs in Rust, not Python

1. **It runs inside the engine's data + algorithms.** The signal is computed from
   each card's FSRS `memory_state` and the `fsrs` crate's
   `current_retrievability_seconds`, plus `revlog.taken_millis` — all owned by the
   Rust core. Doing it elsewhere means re-exporting raw card/revlog rows and
   re-implementing FSRS retrievability, duplicating engine logic.
2. **Performance on 50k cards.** It must back a dashboard within the §10 budget
   (p95 < 150 ms). In Rust it's **one `tag:pgre::*` card scan + one streamed
   note-tag predicate pass** (not 50k point reads), one hoisted `FSRS` instance,
   `f64` accumulators, and an O(n) `select_nth_unstable` median. Measured
   (`just bench`, release, 50k) **p50 32 / p95 33 / p99 33 ms** — ~4.5× under the
   p95 target. The Python equivalent would be N per-card RPC round-trips across
   the FFI — orders of magnitude slower.
3. **Shared by both apps for free.** Because it lives in `rslib`, the _same_ RPC
   is served to the desktop (PyO3) and the iOS app (C-FFI) with no reimplementation
   — proven by the iOS-FFI test calling `topic_mastery` and getting identical
   results (S6), and by matching `buildhash`. The **same engine change ships to
   both the desktop app (PyO3 bridge) and the iOS app (C-FFI) — same `buildhash`,
   including the new iOS device build** (`SpeedrunApp-iOS-device-unsigned.ipa`).

## Required artifacts (§7a checklist)

- **≥3 Rust unit tests + 1 Python test:** **26 Rust speedrun unit+perf tests
  pass** (1 ignored)
  ([rslib/src/speedrun/tests_correctness.rs](../rslib/src/speedrun/tests_correctness.rs),
  `mod test` in [mod.rs](../rslib/src/speedrun/mod.rs), and the 50k perf test in
  [tests_perf.rs](../rslib/src/speedrun/tests_perf.rs)); **9 Python cross-language
  speedrun tests** in [pylib/tests/test_speedrun.py](../pylib/tests/test_speedrun.py).
  The full Rust suite (`just check`) is **570 passed / 1 skipped**.
- **Undo still works / no corruption:** the change is **read-only**. The test
  `rpc_is_read_only_and_preserves_integrity` calls the RPC 100× and asserts the
  undo stack, card/note/revlog counts, and a full `check_database()` are all
  unchanged/clean. Separately, `just speedrun-crash-test` SIGKILLs the engine
  mid-write 50× with **0 corrupted collections**.
- **Why-Rust note:** this document.
- **Upstream files touched + merge difficulty:** below.

## Upstream files touched (and merge difficulty)

Line counts are approximate. Two groups: (A) the **Rust engine change** (this
§7a deliverable) has a tiny upstream footprint; (B) the **wider fork UI**
(manifold home screen, blackboard subject screens, Speed Recall) touches a few
more Qt files more substantively. Listed separately so nothing is hidden.

### A. The Rust change (TopicMastery RPC) — trivial registrations only

| Upstream file              | ~Lines | What                                                            | Merge risk |
| -------------------------- | ------ | --------------------------------------------------------------- | ---------- |
| `rslib/src/lib.rs`         | 1      | `pub mod speedrun;`                                             | trivial    |
| `rslib/proto/src/lib.rs`   | 1      | `protobuf!(speedrun, "speedrun");`                              | trivial    |
| `rslib/proto/python.rs`    | 1      | `import anki.speedrun_pb2` in the generated-Python preamble     | trivial    |
| `pylib/anki/collection.py` | 2      | `self.speedrun = SpeedrunManager(self)` + import                | trivial    |
| `qt/aqt/mediasrv.py`       | 3      | register the `speedrun-dashboard` page + expose `topic_mastery` | trivial    |

All engine logic is in **new files**: `proto/anki/speedrun.proto`,
`rslib/src/speedrun/**`, `pylib/anki/speedrun.py`, `pylib/tests/test_speedrun.py`,
`ts/routes/speedrun-dashboard/**`.

### B. Wider fork UI + build (not part of the §7a Rust change)

| Upstream file                | ~Lines | What                                                                                            | Merge risk                                    |
| ---------------------------- | ------ | ----------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `qt/aqt/main.py`             | ~25    | new `manifold` + `speedRecall` `MainWindowState`s, setup/state handlers, first-run deck seeding | moderate — adds enum variants + dispatch arms |
| `qt/aqt/overview.py`         | ~15    | render the chalkboard for subject decks (incl. when the deck is finished)                       | moderate — new branch in `_renderPage`        |
| `qt/aqt/toolbar.py`          | small  | manifold home integration                                                                       | low                                           |
| `Cargo.toml`                 | 1      | add `mobile/anki-ffi` workspace member                                                          | trivial                                       |
| `Cargo.lock`                 | ~11    | resolved deps for the new crate                                                                 | regenerated                                   |
| `justfile`                   | ~19    | `speedrun-*` / `bench` recipes                                                                  | additive                                      |
| `docs/index.md`, `CLAUDE.md` | few    | doc links                                                                                       | trivial                                       |

New UI/support files (don't exist upstream): `qt/aqt/manifold.py`,
`qt/aqt/pgre.py`, `qt/aqt/speedrecall.py`, `qt/aqt/blackboard/**`,
`qt/aqt/data/decks/**`, `qt/tests/test_{pgre,blackboard,speedrecall}.py`,
`ts/tests/e2e/**`, `mobile/**`, `speedrun/**`.

**Assessment:** merging the **Rust change** upstream is trivial (5 one-line
registrations + new files). The wider fork is a **moderate** merge — `main.py`
and `overview.py` add new `MainWindowState` variants and a render branch (new
code, not rewritten upstream bodies), so conflicts would be small and mechanical.
After a big upstream pull, regenerate `Cargo.lock` and re-run codegen.
