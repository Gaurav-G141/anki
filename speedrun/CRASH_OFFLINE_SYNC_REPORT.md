# Crash / Offline / Sync test report (for a future agent)

**Date:** 2026-07-01. **Scope:** empirically test what happens on (a) a crash
mid-review, (b) working offline then reconnecting, for the Speedrun PGRE fork
(desktop). **No repo code was modified to run these** — only throwaway harnesses
in the session scratchpad. Exam: Physics GRE.

## TL;DR

| Scenario                                          | Result                                                                                         | Notes                                                          |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Engine SIGKILL mid-write ×30                      | ✅ **0/30 corrupted**                                                                          | SQLite transactional rollback                                  |
| SIGKILL mid Speed-Recall answer ×20               | ✅ **0/20 corrupted**, schedule valid JSON, **0 committed entries lost**                       | `speedRecallSched` config write is atomic                      |
| Offline Speed-Recall session → restart            | ✅ **0 lost**, integrity clean, queue rebuilds                                                 | Speed Recall has **no network dependency** (pure local config) |
| Two-device offline → reconnect (native Anki sync) | ✅ **PASS (reproduced 2×)**: both devices converge to all changes, **no loss, no duplication** | Only when each device runs in its **own process** (see gotcha) |

**Bottom line:** crash safety and offline durability hold as expected. Native
Anki sync also merges offline divergence correctly — but only proven for the
**add/add** case, and it exercises **stock Anki sync (the fork does not modify
`rslib/src/sync/**` or `pylib/anki/sync`)**. Two-way _device/phone_ sync is the
Speedrun **Friday** deliverable and is _not_ wired yet; this test used the
built-in Anki sync server as a stand-in.

---

## 1. Crash mid-review

**Method.** Reuse `speedrun/crash_test.py` (spawns a child hammering DB writes,
SIGKILLs it mid-write, reopens + `fix_integrity`). Plus a Speed-Recall-specific
variant that hammers `aqt.speedrecall.record_answer` (which writes the
`speedRecallSched` collection-config JSON) and SIGKILLs mid-write.

**Commands.**

```
just speedrun-crash-test 30        # general engine
# Speed-Recall variant: scratchpad/sr_crash_test.py 20  (see script below)
```

**Results.**

- General: `corrupted collections: 0 / 30`.
- Speed Recall: `0/20 corrupted`, every reopen `valid_json=True`, and the saved
  schedule entry count was **monotonic** (e.g. 164→166 across rounds) — the
  in-flight write rolled back, all _committed_ entries survived. No lost graded
  work.

**Why it holds:** every write (note add, `answer_card`, `set_config`) runs inside
a SQLite transaction; an abrupt kill rolls back the partial write on reopen.

---

## 2. Offline operation & durability

**Method.** Import `anki-decks/Speed_Recall_Formulas.apkg` into a temp
collection; record 30 Speed-Recall answers (local only); `close()` (= quit) then
reopen (= relaunch) and recount; also grep the module for any network use.

**Results.**

- `grep` of `qt/aqt/speedrecall.py` → **no** `socket`/`requests`/`urllib`/`http`/
  `sync` usage. Speed Recall is entirely local (collection config).
- recorded offline: 30 → present after restart: **30 (lost: 0)**; integrity
  clean; queue still builds offline.

**Why it holds:** reviewing is 100% local in Anki; network is only for sync. The
Speed-Recall schedule lives in the collection, so it persists across restarts and
would sync with the collection when online.

---

## 3. Offline → reconnect (two-device sync)

### What was tested

Native Anki sync via the **built-in sync server** (`anki.syncserver`), two
"devices" A and B sharing one account:

1. A creates baseline (3 notes) → full-upload. B → full-download (sees 3).
2. **Offline divergence:** A adds 10 notes (`aoff`), B adds 10 notes (`boff`).
3. **Reconnect:** sync A, sync B, sync A.
4. Expect both devices = 3 + 10 + 10 = **23**, no loss, no duplication.

### Result: ✅ PASS (reproduced twice)

```
A count: total=23 base=3 aoff=10 boff=10
B count: total=23 base=3 aoff=10 boff=10
```

Both devices' offline additions merged cleanly on reconnect.

### ⚠️ CRITICAL GOTCHA for the next agent

The result is only correct when **each device runs in its own OS process**.
An earlier harness created both `Collection` objects **in one Python process**
and got **incoherent** output — `sync_collection` returning `NO_CHANGES` yet only
1–2 of 10 notes crossing over, totals stuck at 15. That was a **test artifact**
(two `RustBackend`s cross-talking in one process), _not_ an Anki/fork bug. Also:

- Full sync requires the real sequence
  `col.close_for_full_sync()` → `col.full_upload_or_download(auth, server_usn=None, upload=?)`
  → `col.reopen(after_full_sync=True)`. Skipping close/reopen leaves a stale handle.
- Reset the server's `SYNC_BASE` dir between runs, or state contaminates.
- Odd but harmless: `sync_collection` returned `NO_CHANGES` on the reconnect
  passes even though the merge happened — trust the final note counts, not that
  label.

### NOT yet tested (future work)

- **Same-card conflict** (§7b): edit the _same_ card on both devices offline,
  sync, and confirm the conflict rule picks one clear winner with no corruption.
  Only add/add divergence was tested here.
- **UI-driven** sync (two desktop profiles against a local server) — closer to
  real usage than the scripted API.
- **Phone ↔ desktop** two-way sync — the Speedrun **Friday** deliverable; not
  implemented (`mobile/` app does reviews on the shared engine but no sync yet).
- Offline-mid-sync interruption, wrong device clock, media sync.

---

## How to reproduce (scripts)

Start a fresh local sync server:

```
SB=$(mktemp -d)
SYNC_USER1="u:p" SYNC_BASE="$SB" SYNC_HOST=127.0.0.1 SYNC_PORT=27736 \
  PYTHONPATH=out/pylib out/pyenv/bin/python -c "import anki.syncserver as s; s.run_sync_server()" &
```

Drive each device as an **isolated subprocess** (this is the key). The helper
`sync_device.py` opens the collection, `sync_login("u","p", "http://127.0.0.1:27736/")`,
and does exactly one op (`add <tag> <n>` / `sync` / `count`), handling the
full-sync handshake with close→full_upload_or_download→reopen. Sequence:

```
A add base 3; A sync;            # baseline up
B sync;                          # baseline down
A add aoff 10; B add boff 10;    # offline divergence
A sync; B sync; A sync;          # reconnect
A count; B count                 # expect both total=23
```

(Full `sync_device.py` / `sr_crash_test.py` bodies were in the session scratchpad
`.../scratchpad/`; recreate from the description above — they're ~40 lines each.)

## Cleanup note

Several localhost sync-server test processes were started during this session
(ports 27703/27714/27725/27736/27747). Kill with `pkill -f syncserver` if still
running.
