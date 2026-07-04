# Dummy account — see the full app with realistic progress

Both apps start empty, and the three honest scores (**Memory / Performance /
Readiness**) correctly **abstain** until there's enough data. To see the _full_
experience — all three scores populated, with ranges, plus the per-topic dashboard —
load the **dummy account**: a pre-seeded "moderate progress" learner.

Ways in: **Path A** (recommended for graders) — log into a throwaway **AnkiWeb**
account in the app and sync the progress down, from any machine, no terminal.
**Path B** — a local seed (no login/account). **Path C** — the `demo`/`demo`
self-hosted server (two-device demo, local network only).

---

## Path A — AnkiWeb login (recommended, portable)

A throwaway AnkiWeb account already holds the seeded dummy collection. To see the
full app on any machine:

1. Build/run the **fork** app (desktop `just run`, or the DMG / iOS build) — the
   scores are computed by the fork engine, so a stock Anki won't show them.
2. Use a **fresh profile** (desktop: the profile picker → Add; or an empty
   `ANKI_BASE`). This matters — logging in on a profile that already has cards would
   overwrite them.
3. **Sync** (toolbar / person button) → log in with the throwaway credentials:

   | Field    | Value                                          |
   | -------- | ---------------------------------------------- |
   | Username | _throwaway account — see the submission notes_ |
   | Password | _throwaway account — see the submission notes_ |
   | Server   | AnkiWeb (leave the self-hosted URL blank)      |

4. Accept the one-time **full download**. You now have ~2046 real cards with
   confident progress. View the three scores at
   <http://localhost:40000/speedrun-dashboard> (desktop) or the **Scores** screen
   (iOS); the manifold spikes are greened by mastery.

> Verified end-to-end: a fresh login + sync downloads the seeded collection and shows
> **Memory 64% / Performance 81% / Readiness 840**, non-abstaining.
>
> The credentials are a **throwaway** account (safe to expose; rotate/delete after
> grading). Keeping the password out of this public repo — put it in the private
> submission notes, or inline it above if you prefer full self-service.

### Keeping it current after app updates

The dummy is regenerated from the **current build's** own decks + engine, so after
any app change just refresh it in one command (needs `ANKIWEB_USER`/`ANKIWEB_PASS`
in `.env`):

```bash
just dummy-ankiweb   # re-seed from this build's decks + re-upload to AnkiWeb
```

Graders then re-sync (or log in fresh) and get the updated dummy. (`.env` is
git-ignored; the upload force-replaces the throwaway account's collection.)

---

## What you'll see (the seeded progress)

Built by [`speedrun/seed_dummy_account.py`](speedrun/seed_dummy_account.py): it
imports the **real bundled PGRE decks** (LaTeX formula cards, already tagged
`pgre::<subject>`) across all 9 subjects and applies an FSRS memory-state gradient +
graded review history on top. Defaults give **~2046 cards / ~6138 reviews**, **100%
topic coverage**, and a realistic strongest→weakest gradient (each area ~50–72%
mastered):

| Score           | Value   | Range   | Confidence |
| --------------- | ------- | ------- | ---------- |
| **Memory**      | 64%     | 62%–66% | high       |
| **Performance** | 81%     | 80%–82% | high       |
| **Readiness**   | **840** | 840–850 | medium     |

(Readiness is on the real PGRE 200–990 scale, in 10-point steps.) All three are
**non-abstaining** — the script asserts this on every run and prints the live numbers,
which are the source of truth if they drift. The cards are **real physics content**;
only the memory-state + review history are synthesized (no live study run needed) —
stated honestly. It exercises the exact same scoring code the app uses.

---

## Path B — local seed, no login

Requires a one-time build (`just build`). Then seed a throwaway profile and launch:

```bash
# 1. Pick a throwaway base dir and create the default profile folder
BASE=/tmp/pgre-dummy
mkdir -p "$BASE/User 1"

# 2. Seed the dummy collection straight into that profile
PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/seed_dummy_account.py \
  --out "$BASE/User 1/collection.anki2"

# 3. Launch Anki on that base (your real profiles are untouched).
#    ANKI_SINGLE_INSTANCE_KEY lets this run even if another Anki is already open
#    (Anki's single-instance lock is per-USER, not per-base — see Troubleshooting).
ANKI_SINGLE_INSTANCE_KEY=pgre-dummy ANKI_BASE="$BASE" just run
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

## Path C — the `demo` / `demo` self-hosted server (two-device demo)

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

- **AnkiWeb (Path A):** `just dummy-ankiweb` (re-seed + re-upload).
- **Local (Path B):** re-run `seed_dummy_account.py` — it wipes and rebuilds the
  `--out` collection. Tune `--reviews-per` to change the review volume.
- **Self-hosted (Path C):** delete `~/speedrun-sync` and re-bootstrap from the desktop.

## Troubleshooting

**"The app opens but I can't click anything / it crashes on open," or on quit:
`sqlite3.OperationalError: attempt to write a readonly database` (in
`profiles.py … pm.save`).**

Cause: Anki allows only **one instance per user** — the single-instance lock key is
per-user, not per-`ANKI_BASE` (`qt/aqt/__init__.py`: `KEY = … or "anki"+checksum(user)`).
If another Anki is already running (your normal `/Applications/Anki.app`, a previous
`just run`, or the DMG build), launching a second one makes the new process signal
the existing instance and exit immediately — the new window flashes and dies, and the
profile-save contention shows up as the read-only `prefs21.db` error. It is **not** a
data-corruption bug (your collection is fine).

Fix — either:

- **Run it isolated (recommended):** the Path B command above already sets
  `ANKI_SINGLE_INSTANCE_KEY=pgre-dummy`, giving this instance its own lock so it runs
  alongside any other Anki. Use a distinct key per simultaneous instance.
- **Or quit every other Anki first:** the real app (`⌘Q` on `/Applications/Anki.app`),
  any other `just run`, and the DMG build. Then relaunch.

If a window is already wedged, quit all Anki processes and relaunch with the unique
`ANKI_SINGLE_INSTANCE_KEY` above.

## Notes

- Both apps run fully with **AI switched off** (no key) — the coach falls back to the
  precomputed "⚡ Fastest approach" and never fabricates a grade.
- No secrets here: the `demo`/`demo` credentials are for a throwaway local server only.
