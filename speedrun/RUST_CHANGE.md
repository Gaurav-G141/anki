# The Rust engine change (Speedrun §7a)

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
   (p95 < 150 ms). In Rust it's a **single per-subject SQL scan** (9 bulk queries,
   not 50k point reads), one hoisted `FSRS` instance, `f64` accumulators, and an
   O(n) `select_nth_unstable` median. Measured **release p95 ≈ 51 ms** on 50k
   (3× under target). The Python equivalent would be N per-card RPC round-trips
   across the FFI — orders of magnitude slower.
3. **Shared by both apps for free.** Because it lives in `rslib`, the _same_ RPC
   is served to the desktop (PyO3) and the iOS app (C-FFI) with no reimplementation
   — proven by the iOS-FFI test calling `topic_mastery` and getting identical
   results (S6), and by matching `buildhash`.

## Required artifacts (§7a checklist)

- **≥3 Rust unit tests + 1 Python test:** 18 Rust tests
  ([rslib/src/speedrun/tests_correctness.rs](../rslib/src/speedrun/tests_correctness.rs),
  `mod test` in [mod.rs](../rslib/src/speedrun/mod.rs), and the 50k perf test in
  [tests_perf.rs](../rslib/src/speedrun/tests_perf.rs)); Python cross-language
  tests in [pylib/tests/test_speedrun.py](../pylib/tests/test_speedrun.py).
- **Undo still works / no corruption:** the change is **read-only**. The test
  `rpc_is_read_only_and_preserves_integrity` calls the RPC 100× and asserts the
  undo stack, card/note/revlog counts, and a full `check_database()` are all
  unchanged/clean. Separately, `just speedrun-crash-test` SIGKILLs the engine
  mid-write 50× with **0 corrupted collections**.
- **Why-Rust note:** this document.
- **Upstream files touched + merge difficulty:** below.

## Upstream files touched (and merge difficulty)

All logic lives in **new files**; only tiny registrations touch tracked upstream
files. Total upstream delta: **10 files, +45 lines** (`git diff --stat`).

| Upstream file                | Lines added | What                                                            | Merge risk            |
| ---------------------------- | ----------- | --------------------------------------------------------------- | --------------------- |
| `rslib/src/lib.rs`           | 1           | `pub mod speedrun;`                                             | trivial               |
| `rslib/proto/src/lib.rs`     | 1           | `protobuf!(speedrun, "speedrun");`                              | trivial               |
| `rslib/proto/python.rs`      | 1           | `import anki.speedrun_pb2` in the generated-Python preamble     | trivial               |
| `pylib/anki/collection.py`   | 2           | `self.speedrun = SpeedrunManager(self)` + import                | trivial               |
| `qt/aqt/mediasrv.py`         | 3           | register the `speedrun-dashboard` page + expose `topic_mastery` | trivial               |
| `Cargo.toml`                 | 1           | add `mobile/anki-ffi` workspace member                          | trivial               |
| `Cargo.lock`                 | 11          | resolved deps for the new crate                                 | regenerated           |
| `justfile`                   | 19          | `speedrun-*` / `bench` recipes                                  | additive, no conflict |
| `docs/index.md`, `CLAUDE.md` | 3+3         | doc links                                                       | trivial               |

**New files** (zero merge risk — they don't exist upstream):
`proto/anki/speedrun.proto`, `rslib/src/speedrun/**`, `pylib/anki/speedrun.py`,
`pylib/tests/test_speedrun.py`, `ts/routes/speedrun-dashboard/**`,
`ts/tests/e2e/speedrun-dashboard.test.ts`, `mobile/**`, `speedrun/**`.

**Assessment:** a future upstream merge is **easy**. Every edit to a shared file
is a single additive line/registration in a list; no upstream function bodies were
modified. The only mechanical follow-up after a big upstream pull would be
regenerating `Cargo.lock` and re-running codegen.
