# Manual End-to-End Test — S0–S3

How to verify, by hand, that the base fork builds + runs (S0), the PGRE deck
tooling works (S1), and the memory-score engine change works (S2/S3). Commands
are run from the repo root. The toolchain (`rustup`, `ninja`, `just`) is already
installed.

> If `cargo`/`rustc` aren't found in a new terminal, run:
> `source "$HOME/.cargo/env"` (or add `~/.cargo/bin` to your PATH).

## S0 — the base builds and runs

1. **Build** (already done once; re-runs are fast):
   ```bash
   just build
   ```
   Expected: completes with no error.

2. **Run the desktop app** — use a **throwaway profile** so your real Anki
   collection is never touched:
   ```bash
   ANKI_BASE=/tmp/pgre-anki just run
   ```
   Expected: the Anki window opens on an empty throwaway profile. Create a note
   (Add), then study it (Review) to confirm the engine works. Close when done.
   (Your real collection lives elsewhere and is untouched.)

3. **Full checks** (optional, ~few min):
   ```bash
   just check
   ```
   Expected: **fully green** — provided the installer template submodule is
   initialized once (it's a git submodule, empty on a fresh clone):
   ```bash
   git submodule update --init qt/installer/mac-template
   ```
   Without that, the two `qt/tests/test_installer.py` tests
   (`test_build_and_package`, `test_compile_fails_loudly`) fail at "Unable to
   clone application template" — they `briefcase build` against
   `qt/installer/mac-template`, which is empty until the submodule is checked
   out. (This is Anki infrastructure, unrelated to Speedrun; full Xcode is also
   required for the build step.) With the submodule initialized + Xcode
   installed, everything passes: Rust build + clippy, the full Rust test suite
   (incl. 18 Speedrun tests + the iOS-FFI crate), ruff, mypy, format, minilints,
   vitest (incl. the dashboard tests), and the qt pytest suite.

## S1 — PGRE deck fixtures

1. **Generate the fixtures:**
   ```bash
   just speedrun-fixtures
   ```
   Expected: writes `out/speedrun/{pgre_main,pgre_missing_highweight,pgre_empty}.colpkg`
   plus `out/speedrun/manifest.json`, and prints per-fixture counts
   (pgre_main: 9 subjects, 54 cards).

2. **Run the S1 gate:**
   ```bash
   just speedrun-test
   ```
   Expected: a JSON report ending with `"gate": "GREEN"`, `"failed": 0`, and exit
   code 0. (11 checks: one-subject-tag-per-note, full subject coverage,
   integrity, valid `.colpkg`, plus the missing-high-weight and empty cases.)

3. **See the tagged deck in the app** (visual check, throwaway profile):
   ```bash
   ANKI_BASE=/tmp/pgre-view just run
   ```
   In Anki: **File → Import →** choose `out/speedrun/pgre_main.colpkg` →
   confirm replacing the (empty) throwaway collection. Then:
   - The deck list shows **PGRE → Classical Mechanics, Electromagnetism, …**
     (9 subdecks).
   - **Browse** and search `tag:pgre::classical_mechanics` → 6 cards; the sidebar
     lists all `pgre::*` tags.
   - Optional: import `pgre_missing_highweight.colpkg` into another throwaway
     profile → note there is **no** Classical Mechanics deck (this is what later
     makes the readiness dashboard abstain).

   Headless alternative (no GUI):
   ```bash
   PYTHONPATH=out/pylib out/pyenv/bin/python - <<'PY'
   from anki.collection import Collection
   c = Collection("out/speedrun/work/pgre_main.anki2")
   print("cards:", c.card_count(), "tags:", [t for t in c.tags.all() if t.startswith("pgre")])
   print("classical_mechanics cards:", len(c.find_cards("tag:pgre::classical_mechanics")))
   c.close()
   PY
   ```

## Manual prerequisite (for the iOS companion, S6/S7)

Install **full Xcode** from the App Store, open it once, then:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

This is required for the iOS companion (the Rust iOS targets
`aarch64-apple-ios{,-sim}` are already installed). Note: Xcode does **not** make
the two `test_installer.py` tests pass — those need the Briefcase macOS template
provisioned into the (currently empty, git-ignored) `qt/installer/mac-template`,
which is a separate release/packaging concern unrelated to S0–S3.

## S2 & S3 — the memory-score engine change (`SpeedrunService.TopicMastery`)

S2 is the real Rust change: a read-only backend RPC that scans the PGRE-tagged
collection and returns per-topic mastery plus an honest, range-bearing memory
score. S3 is the scoring math (mastered-fraction + Wilson 95% interval, with a
give-up rule). It lives in new files only — `proto/anki/speedrun.proto` and
`rslib/src/speedrun/` — plus one line registering the module in
[rslib/src/lib.rs](rslib/src/lib.rs).

1. **Rust tests (correctness + read-only/undo safety):**
   ```bash
   cargo test -p anki speedrun
   ```
   Expected: 17 tests pass (scoring math, mastered-count boundary,
   accuracy-vs-golden, None-handling, give-up boundaries, missing-high-weight
   abstain, determinism, honesty contract, param overrides, Wilson fuzz, and a
   100×-call read-only + `dbcheck`-clean proof).

2. **Performance (50,000 cards):**
   ```bash
   cargo test -p anki speedrun::tests_perf -- --ignored --nocapture
   ```
   Expected: builds 50k cards (~6 s) and prints a p50/p95/p99 table; asserts
   **p95 < 150 ms** and **p99 < 250 ms**. (Passes even in a debug build — release
   is much faster.)

3. **Python cross-language:**
   ```bash
   just test-py            # includes pylib/tests/test_speedrun.py
   # or just that file:
   PYTHONPATH=out/pylib ANKI_TEST_MODE=1 out/pyenv/bin/python -m pytest pylib/tests/test_speedrun.py -v
   ```

4. **The honest score, by hand (CLI demo):**
   ```bash
   just speedrun-fixtures            # if not already generated
   just speedrun-mastery             # defaults to out/speedrun/work/pgre_main.anki2
   ```
   Expected on `pgre_main`: an **ABSTAIN** card with the reason
   _"no FSRS memory-state data yet"_ — correct, because that fixture has reviews
   but no FSRS memory state. To see the same abstain logic for a missing
   high-weight section:
   ```bash
   just speedrun-mastery col=out/speedrun/work/pgre_missing_highweight.anki2
   ```
   (abstains, citing missing **Classical Mechanics**).

5. **See a _scored_ (non-abstaining) result** — needs real FSRS memory state,
   which the engine computes when you actually review with FSRS enabled:
   - Launch a throwaway profile: `ANKI_BASE=/tmp/pgre-score just run`
   - Import a PGRE deck (`out/speedrun/pgre_main.colpkg`, or the downloaded
     `extra/decks/Physics_GRE.apkg` — see below), ensure **FSRS is enabled**
     (Deck Options → FSRS; it is on by default in this build), and **review ≥ 20
     cards**.
   - Quit, then point the demo at that profile's collection:
     ```bash
     just speedrun-mastery col="$(ls -t /tmp/pgre-score/**/collection.anki2 | head -1)"
     ```
     Expected: a memory score (mastered %) with a Wilson `[low, high]` range,
     coverage %, a confidence label, the weakest-topics reasons, and a per-topic
     table — i.e. the full honest score card, no bare number.

> Real Physics-GRE content for step 5 is already downloaded at
> `extra/decks/Physics_GRE.apkg` (108 cards). It is one flat deck, so to feed the
> per-topic dashboard you'd tag it via `speedrun/tag_deck.py` (see
> [speedrun/README.md](speedrun/README.md)); untagged, it still exercises the
> review loop and FSRS memory-state generation.

## S4 — Python wrapper (`col.speedrun`)

So callers never touch `col._backend`:

```bash
PYTHONPATH=out/pylib ANKI_TEST_MODE=1 out/pyenv/bin/python -m pytest pylib/tests/test_speedrun.py -v
```

Expected: 5 pass, including `test_public_wrapper` (calls `col.speedrun.topic_mastery()`
— no `_backend`, no manual pb2 import — and checks defaults + override pass-through).

## S5 & S8 — the desktop dashboard

A SvelteKit page at `/speedrun-dashboard` that renders the honest score card (or
the abstain state) + a per-topic table including **median latency** (S8), behind a
mapper that makes it structurally impossible to show a bare number.

```bash
just test-ts        # includes ts/routes/speedrun-dashboard/lib.test.ts (14 tests)
just lint           # svelte-check + tsc clean
```

See it live in the app (the RPC is now exposed via mediasrv):

```bash
ANKI_BASE=/tmp/pgre-dash just run
# In Anki's web debugger, or once wired to a menu, open:
#   http://localhost:40000/speedrun-dashboard
```

On an empty/SM-2 profile it shows the **abstain** card; after FSRS reviews
(step 5 above) it shows the score card with range, coverage, confidence,
reasons, and the per-topic latency column.

## S6 — iOS C-FFI (shared engine)

A tiny C ABI around the Rust backend, packaged as an xcframework — proves iOS
runs the _same_ engine.

```bash
cargo test -p anki-ffi                       # 6 pass (round-trip, parity, open+query, 10k-loop)
mobile/build-xcframework.sh                  # builds mobile/AnkiCore.xcframework (device + sim)
```

`cargo test -p anki-ffi` includes the **engine-parity** check: the `buildhash()`
linked into the FFI equals the desktop build's (`out/buildhash`), proving it's
the same engine, not a reimplementation.

## S9 — installer + crash-safety

- **Installer build** (needs the submodule from S0 step 3 + Xcode):
  ```bash
  PYTHONPATH=pylib:out/pylib:out/qt:out/qt/tools ANKI_TEST_MODE=1 \
    out/pyenv/bin/pytest -p no:cacheprovider qt/tests/test_installer.py -v
  ```
  Expected: all pass (the Briefcase macOS build assembles the app bundle).
  A full packaged `.dmg` + clean-machine install + screen recording is the
  manual "proof" step.
- **Crash safety (S9-T02):** SIGKILL the engine mid-write and prove no corruption:
  ```bash
  just speedrun-crash-test            # 50 rounds (stricter than the spec's 20)
  ```
  Expected: every round reopens **clean**; `corrupted collections: 0 / 50`.

## S7 — iOS SwiftUI app (shared engine, in the Simulator)

A minimal SwiftUI app (`mobile/SpeedrunApp/`) that opens the bundled deck and runs
a real review loop on the **same Rust engine** via the S6 C-FFI (no scheduler
reimplementation). Needs Xcode + an iOS Simulator runtime
(`xcodebuild -downloadPlatform iOS` once).

```bash
export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"
cd mobile/SpeedrunApp
# build for the simulator (must pass):
xcodebuild -scheme SpeedrunApp \
  -destination 'platform=iOS Simulator,name=iPhone 17' build CODE_SIGNING_ALLOWED=NO
# automated 20-review check (XCUITest drives Show-Answer + grade x20):
xcodebuild -scheme SpeedrunApp \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: **BUILD SUCCEEDED**, then **TEST SUCCEEDED** (`testTwentyReviews`). The
test verifies 20 graded answers persist to `Documents/collection.anki2` with
nonzero `taken_millis` (the latency signal), through the shared engine. To do it
by hand and confirm on desktop, see the step list the build prints / the
`mobile/SpeedrunApp/` README notes (boot the sim, install, launch
`net.ankiweb.speedrun`, tap Show Answer + a grade ≥20×, then open the app's
`Documents/collection.anki2` in desktop Anki).

> swift-protobuf resolves from its normal SwiftPM remote. In this sandboxed
> environment a leftover git config can block the clone; the build wraps the one
> xcodebuild call with `GIT_CONFIG_VALUE_0=all` (no persisted change). On a normal
> machine that isn't needed.
