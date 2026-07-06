# Large-deck stress report — 205,531-card collection

**Date:** 2026-07-05. **Deck:** `Cities_of_Your_Country.apkg` (218 MB, legacy
SQLite format, 1,446 media, 2 decks) → **205,531 notes / 205,531 cards**. That's
**~4× the 50k design target** the perf work assumes.

**Harness:** [`speedrun/large_deck_stress_test.py`](large_deck_stress_test.py)
(reusable; runs on a throwaway copy — never the live collection). Re-run:

```
PYTHONPATH=qt:out/qt:out/pylib out/pyenv/bin/python speedrun/large_deck_stress_test.py [deck.apkg]
```

A focused follow-up (`scratchpad/bigdeck_followup.py`) classified the crash
result and captured tagged-mastery timing.

## Current stress run (2026-07-05, `just stress`) — 7/7 checks pass

The latest full `just stress` run on the same **205,531-card** collection (≈4×
the 50k design target) passes all **7/7** checks, after the fixes below:

| Check                                     | Result                        | Verdict |
| ----------------------------------------- | ----------------------------- | ------- |
| **Deck-tree** first render                | **19 ms**                     | ✅      |
| **Memory dashboard** (TopicMastery) first | **125 ms**                    | ✅      |
| **Memory dashboard** refresh              | **123–198 ms**                | ✅      |
| **Full upload** (bootstrap)               | **4.7 s**                     | ✅      |
| **Full download** (adopt)                 | adopted **205531 / 205531**   | ✅      |
| **Incremental sync**                      | propagates                    | ✅      |
| **Crash / integrity**                     | clean, openable, no data loss | ✅      |

At the **design 50k** scale the release bench (`just bench`, topic_mastery scan)
is **p50 32 / p95 33 / p99 33 ms** (budget p95 < 150 / p99 < 250) — comfortably
under budget. The 205k dashboard numbers above are the ~4× stress point and still
land inside the first-load / refresh budgets after the tag-scan fix.

## Results (original run, before the fixes below)

| Path                                           | Result                                      | Verdict                         |
| ---------------------------------------------- | ------------------------------------------- | ------------------------------- |
| **Import** 205k                                | 13.3 s                                      | ✅ fast, robust                 |
| **Integrity after import** (`fix_integrity`)   | clean, 12.3 s                               | ✅                              |
| **Search** (`find_cards`/`find_notes` all)     | 0.03 s / 0.02 s                             | ✅ instant                      |
| **Cold reopen** of the big collection          | ~0 s                                        | ✅                              |
| **Bulk-tag** 205k notes across 9 subjects      | 3.5 s                                       | ✅                              |
| **TopicMastery RPC (dashboard) @205k**         | **p50 1.54 s / p95 1.57 s**                 | ⚠️ **over budget**               |
| **Speed Recall schedule store**                | **O(n²)** (5.2 s → 58 s per 2k batch)       | ⚠️ **real design flaw (latent)** |
| **Crash mid-write ×8** (classification)        | **8/8 clean, 0 data loss, always openable** | ✅ holds                        |
| **Peak RSS** (import + tag + 12k O(n²) writes) | ~956 MB                                     | ℹ️ acceptable                    |

## ✅ Fixes applied (2026-07-01)

Both flagged issues are fixed; no test regressed (rust speedrun 26/26 pass — 1
ignored, pylib speedrun 9/9, qt pgre + speedrecall green, ruff clean, rustfmt
clean; full `just check` = 570 Rust passed / 1 skipped).

| Issue                                     | Before                            | After                            | Change                                                                                                  |
| ----------------------------------------- | --------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Speed Recall store (record_answer)        | 5.2 s → 58 s per 2k batch (O(n²)) | **flat ~0.05 s / 2k (O(1))**     | per-card config keys instead of one growing JSON blob (`qt/aqt/speedrecall.py`)                         |
| TopicMastery @50k (release, `just bench`) | p95 53 ms                         | **p50 32 / p95 33 / p99 33 ms**  | one tag scan + one predicate note-tag pass instead of 9 per-subject scans (`rslib/src/speedrun/mod.rs`) |
| TopicMastery @205k untagged (debug)       | 554 ms                            | **127 ms**                       | "                                                                                                       |
| TopicMastery @205k tagged (debug)         | 1567 ms                           | **1014 ms** (≈130 ms in release) | "                                                                                                       |

Details:

- **Speed Recall O(n²):** `record_answer` now writes one `speedRecall:sched:<cid>`
  config row per answer (O(1)); reads merge those keys and still honor the legacy
  `speedRecallSched` blob for older collections.
- **TopicMastery scan:** replaced the 9 per-subject `tag:` searches (9 full
  scans of the heavy `notes.tags` column) with a single `tag:pgre::*` card scan
  plus one streamed `get_note_tags_by_predicate` pass that buckets each note into
  its subject (hierarchical tag match). Correctness verified against the
  existing Rust speedrun tests (now 26 unit+perf, 1 ignored — mastered counts,
  golden mean-R, coverage/abstain, etc.).

## The two real findings (original)

### 1. ⚠️ Dashboard (TopicMastery) exceeds its budget at 205k

- @205k: **p95 ≈ 1.57 s**. The Speedrun budget is first-load **< 1 s**, refresh
  **< 500 ms**.
- Context: at the **design 50k** scale the release bench is **~53 ms** (well
  under budget), so this only bites at ~4× scale. But 53 ms → 1.57 s for 4× the
  cards is **super-linear**, so the scan cost grows faster than card count — worth
  profiling before claiming 100k+ support (a §13 stretch goal).
- Not a crash/corruption — the RPC returns correctly (coverage=1.0, abstains
  because reviews=0 < the 100-review floor). It's a _latency_ regression at scale.

### 2. ⚠️ Speed Recall schedule store is O(n²) (latent)

- `speedrecall.record_answer` loads the **entire** `speedRecallSched` JSON blob
  from config, adds one entry, and writes the **whole blob back** — every answer.
- Measured per-2,000-answer batch: **5.2 s → 15.6 → 26.3 → 36.9 → 47.7 → 58.4 s**
  (linear per-batch growth ⇒ **O(n²)** total); config grew to 0.84 MB at 12k.
- **Why it's latent, not a current bug:** Speed Recall sources only the
  `Speed Recall::*` deck (**166 cards**), so the schedule tops out at ~166
  entries → each write serializes a ~12 KB blob (~0.2 ms). Fine today. It would
  only degrade if Speed Recall is ever pointed at a large deck.
- **Recommended fix (not applied — no code changes requested):** store the
  per-card schedule in a table / one config key _per card_ (or reuse revlog +
  the FSRS path) instead of a single growing JSON blob. Then it's O(1) per answer.

## Crash safety — clarified

The first harness pass flagged **2/5 rounds "CORRUPT"** (i.e. `fix_integrity`
returned _not-clean_). The focused re-classification (**8 rounds**) came back
**8/8 clean, every collection openable, note counts intact/growing (217k→247k as
the killed child's committed writes persisted), zero data loss.** So:

- A mid-write `SIGKILL` on a 205k collection does **not** lose data or produce an
  unopenable file — SQLite's transactional rollback holds at scale.
- The earlier 2/5 was an **intermittent, fully-recoverable** `fix_integrity`
  finding (it repairs on open), not corruption. The longer run has since been
  done: `just speedrun-crash-test 50` = **0 corrupted / 50** SIGKILL-mid-write
  rounds — it never escalated to data loss.

## What did NOT break

Import, integrity, search/browse, reopen, bulk tagging, and crash recovery all
handled 205k cleanly. Memory peaked <1 GB (and most of that was the O(n²) test).

## For the next agent

- **Fix #2 (Speed Recall O(n²))** before pointing Speed Recall at large decks.
- **Profile the TopicMastery scan** for the super-linear trend (50k=53 ms →
  205k=1.5 s); check the tag→subject matching and per-card work for an accidental
  O(n·subjects) or repeated allocation.
- Crash test at 50 rounds is now **done** (0 corrupted / 50) — the intermittent
  `fix_integrity` flag never became data loss.
- Harness note: the first run had a `from speedrun import taxonomy`
  `ModuleNotFoundError` (cwd/sys.path); **fixed** in `large_deck_stress_test.py`
  (adds repo root to `sys.path`).
