# Dummy account — see the full app with realistic progress

Both apps start empty, and the three honest scores (**Memory / Performance /
Readiness**) correctly **abstain** until there's enough data. To see the _full_
experience — all three scores populated, with ranges, plus the per-topic dashboard —
load the **dummy account**: a pre-seeded "moderate progress" learner.

There are two ways in. **Path A** (local seed, no login) works on any machine and is
the fastest way to see everything. **Path B** (the `demo`/`demo` sync account) is for
demoing two-device sync.

---

## What you'll see (the seeded progress)

Built by [`speedrun/seed_dummy_account.py`](speedrun/seed_dummy_account.py) — all 9
PGRE subjects, an FSRS memory-state gradient, and graded review history. With the
defaults (`--cards-per 14 --reviews-per 6`) that's **126 cards / 756 reviews**,
**100% topic coverage**, and a realistic strongest→weakest gradient across subjects:

| Score           | Value   | Range   | Confidence |
| --------------- | ------- | ------- | ---------- |
| **Memory**      | 57%     | 48%–65% | high       |
| **Performance** | 72%     | 69%–75% | high       |
| **Readiness**   | **770** | 740–790 | medium     |

(Readiness is on the real PGRE 200–990 scale, in 10-point steps.) All three are
**non-abstaining** — the script asserts this on every run and prints the live numbers,
which are the source of truth if they drift.

> The progress is **synthetic** (seeded memory-state + revlog, not a live study run) —
> stated honestly. It exercises the exact same scoring code paths the app uses.

---

## Path A — desktop, no login (fastest, portable)

Requires a one-time build (`just build`). Then seed a throwaway profile and launch:

```bash
# 1. Pick a throwaway base dir and create the default profile folder
BASE=/tmp/pgre-dummy
mkdir -p "$BASE/User 1"

# 2. Seed the dummy collection straight into that profile
PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/seed_dummy_account.py \
  --out "$BASE/User 1/collection.anki2"

# 3. Launch Anki on that base (your real profiles are untouched)
ANKI_BASE="$BASE" just run
```

The app opens the seeded collection directly (`ANKI_BASE/<profile>/collection.anki2`).
The seed marks the fork's first-run bundled-deck import as already done, so nothing
dilutes the scores. Then:

- Open the **memory/mastery dashboard** in any browser:
  <http://localhost:40000/speedrun-dashboard> — three score cards (each with a range,
  coverage %, confidence, "last updated", and weakest-topic reasons) + a per-topic
  table (mastered / mean recall / median latency).
- Try **⚛️ Practice MCQs** (Performance section / atom toolbar button) to see the
  real-exam quiz and the AI Heuristic Coach.

**Fallback (if you'd rather import):** the pattern in
[`speedrun/MANUAL_TEST.md`](speedrun/MANUAL_TEST.md) — launch on a throwaway
`ANKI_BASE`, then **File → Import** a `.colpkg`. (Export one from the seeded
collection first if you go this route.)

---

## Path B — the `demo` / `demo` sync account (two-device demo)

Use this to show a review on the phone appearing on the desktop (and the reverse).
Full details in [`speedrun/SYNC.md`](speedrun/SYNC.md); the short version:

| Field    | Value                   |
| -------- | ----------------------- |
| Username | `demo`                  |
| Password | `demo`                  |
| Endpoint | `http://127.0.0.1:8080` |

```bash
# Start the self-hosted sync server (ships in-tree)
export PATH="$HOME/.cargo/bin:$PATH"
SYNC_HOST=0.0.0.0 SYNC_PORT=8080 SYNC_BASE=~/speedrun-sync SYNC_USER1=demo:demo \
  cargo run -p anki-sync-server
```

- **Desktop:** Preferences → Syncing → **Self-hosted sync server** →
  `http://127.0.0.1:8080`, then **Sync** and log in `demo` / `demo`. The first sync
  **bootstraps** the (seeded) desktop collection up to the server.
- **iOS:** tap the sync/person button → log in `demo` / `demo` at the same endpoint
  (the Simulator shares the Mac's loopback, so `127.0.0.1` works). Its first sync is a
  one-time full download that adopts the shared collection; everything after is
  incremental two-way sync.

> This server is **local/demo only** — its key is derived from `demo:demo` and is
> deliberately different from AnkiWeb. A grader on a different machine should use
> **Path A**, or their own AnkiWeb account (leave the endpoint blank).

---

## Where to look (both platforms)

- **Desktop:** `/speedrun-dashboard` (the three scores + per-topic table); **⚛️
  Practice MCQs** for the quiz + AI coach.
- **iOS:** the **Scores** screen (three scores with ranges + give-up rule) and
  **Practice MCQs**.

## Reset / re-seed

- **Local (Path A):** re-run `seed_dummy_account.py` — it wipes and rebuilds the
  `--out` collection. Tune `--cards-per` / `--reviews-per` to change the numbers.
- **Sync (Path B):** delete `~/speedrun-sync` and re-bootstrap from the desktop.

## Notes

- Both apps run fully with **AI switched off** (no key) — the coach falls back to the
  precomputed "⚡ Fastest approach" and never fabricates a grade.
- No secrets here: the `demo`/`demo` credentials are for a throwaway local server only.
