# Manual End-to-End Test — Speedrun (all features, S0–S9)

How to verify, by hand, every feature added on top of Anki for the **Physics GRE**
Speedrun MVP. Run from the repo root.

> If `cargo`/`rustc` aren't found in a fresh terminal:
> `source "$HOME/.cargo/env"` (or add `~/.cargo/bin` to PATH). For iOS commands
> also add Homebrew: `export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"`.

For a requirement-by-requirement audit against the Speedrun brief, see
[SPEEDRUN_COMPLIANCE.md](SPEEDRUN_COMPLIANCE.md).

---

## 0. One-time setup

Already done on this machine, but needed on a fresh clone / a grader's box:

```bash
# toolchain (Rust pinned by rust-toolchain.toml, ninja, just)
brew install just ninja
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# installer template (a git submodule; empty on a fresh clone → installer tests fail without it)
git submodule update --init qt/installer/mac-template

# iOS only (S6/S7): full Xcode from the App Store, opened once, then:
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcodebuild -downloadPlatform iOS          # installs an iOS Simulator runtime
rustup target add aarch64-apple-ios aarch64-apple-ios-sim

# build once (downloads protoc/uv/node; subsequent runs are fast)
just build
```

---

## 1. Verify everything at once

**The automated gate** (build + clippy + all Rust/Python/TS tests + lint + format):

```bash
just check          # expect: fully green, exit 0 ("558 tests run: 558 passed")
```

`just check` deliberately skips the slow/opt-in checks below (the 50k perf test is
`#[ignore]`; the crash and iOS tests aren't in the default suite). Run those
explicitly:

| Feature                      | Command                                                                            | Expected                                              |
| ---------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Deck tooling (S1)            | `just speedrun-test`                                                               | `"gate": "GREEN"`, `"failed": 0`                      |
| Memory RPC + scoring (S2/S3) | `cargo test -p anki speedrun`                                                      | 17 passed                                             |
| Perf on 50k (S2/§10)         | `just bench`                                                                       | p50/p95/p99 table; **release p95 ≈ 51 ms** (< 150 ms) |
| Python wrapper (S4)          | `PYTHONPATH=out/pylib out/pyenv/bin/python -m pytest pylib/tests/test_speedrun.py` | 5 passed                                              |
| Dashboard logic (S5/S8)      | `just test-ts`                                                                     | dashboard `lib.test.ts` 14 passed                     |
| iOS shared engine (S6)       | `cargo test -p anki-ffi`                                                           | 6 passed (incl. buildhash parity)                     |
| Crash safety (S9)            | `just speedrun-crash-test`                                                         | `corrupted collections: 0 / 50`                       |
| iOS app (S7)                 | see §S7 below (`xcodebuild … build` then `… test`)                                 | BUILD + TEST SUCCEEDED                                |

Everything below is the same features, shown interactively / with expected output.

---

## S0 — the base builds and runs

```bash
just build                       # completes with no error
ANKI_BASE=/tmp/pgre-anki just run   # opens Anki on a THROWAWAY profile (your real data untouched)
```

In the window: add a note, then review it — confirms the forked engine runs.

---

## S1 — PGRE deck tooling

```bash
just speedrun-fixtures   # writes out/speedrun/{pgre_main,pgre_missing_highweight,pgre_empty}.colpkg + manifest.json
just speedrun-test       # S1 gate: "gate": "GREEN", "failed": 0
```

See the tagged deck in the app (throwaway profile):

```bash
ANKI_BASE=/tmp/pgre-view just run
# File → Import → out/speedrun/pgre_main.colpkg  (replaces the empty throwaway collection)
```

Then: the deck list shows **PGRE → Classical Mechanics, Electromagnetism, …**
(9 subdecks); **Browse** + search `tag:pgre::classical_mechanics` → 6 cards.

Headless equivalent (no GUI):

```bash
PYTHONPATH=out/pylib out/pyenv/bin/python - <<'PY'
from anki.collection import Collection
c = Collection("out/speedrun/work/pgre_main.anki2")
print("cards:", c.card_count(), "tags:", [t for t in c.tags.all() if t.startswith("pgre")])
print("classical_mechanics cards:", len(c.find_cards("tag:pgre::classical_mechanics")))
c.close()
PY
```

---

## S2 & S3 — the honest memory score (`SpeedrunService.TopicMastery`)

The real Rust engine change (see [RUST_CHANGE.md](RUST_CHANGE.md)): a read-only RPC
that scans PGRE-tagged cards and returns per-topic mastery + a mastered-fraction
score with a **Wilson 95%** range, or **abstains** when data is thin.

```bash
cargo test -p anki speedrun                                   # 17 correctness/undo tests
cargo test -p anki speedrun::tests_perf -- --ignored --nocapture   # 50k perf table (or: just bench)
```

The score, by hand:

```bash
just speedrun-mastery                                    # defaults to pgre_main
```

Expected on `pgre_main`: an **ABSTAIN** card — reason _"no FSRS memory-state data
yet"_ (the fixture has reviews but no FSRS state). Missing-section abstain:

```bash
just speedrun-mastery col=out/speedrun/work/pgre_missing_highweight.anki2
# abstains, citing missing Classical Mechanics (a >=10%-weight subject)
```

**See a real (non-abstaining) score** — needs FSRS memory state, which the engine
computes only when you actually review with FSRS on:

1. `ANKI_BASE=/tmp/pgre-score just run`
2. **File → Import** `out/speedrun/pgre_main.colpkg` (or `extra/decks/Physics_GRE.apkg`).
   In **Deck Options → FSRS** confirm FSRS is enabled (default in this build). If
   only 20 new cards appear, raise **New cards/day** (Deck Options → Daily Limits).
3. Review **≥ 20** cards, then quit.
4. Point the demo at that profile's collection:
   ```bash
   just speedrun-mastery col="$(ls -t /tmp/pgre-score/**/collection.anki2 | head -1)"
   ```
   Expected: memory score (mastered %), Wilson `[low, high]` range, coverage %,
   a confidence label, weakest-topic reasons, and the per-topic table — the full
   honest card, never a bare number.

---

## S4 — Python wrapper (`col.speedrun`)

Callers use the public API, not `col._backend`:

```bash
PYTHONPATH=out/pylib ANKI_TEST_MODE=1 out/pyenv/bin/python -m pytest pylib/tests/test_speedrun.py -v
```

Expected: 5 pass, incl. `test_public_wrapper` (calls `col.speedrun.topic_mastery()`
— no `_backend`, no manual pb2 import — and checks defaults + override pass-through).
Try it live:

```bash
PYTHONPATH=out/pylib out/pyenv/bin/python - <<'PY'
from anki.collection import Collection
c = Collection("out/speedrun/work/pgre_main.anki2")
r = c.speedrun.topic_mastery()
print("abstain:", r.abstain, "| topics:", len(r.topics), "| reasons:", list(r.abstain_reasons))
c.close()
PY
```

---

## S5 & S8 — the desktop dashboard

A SvelteKit page at `/speedrun-dashboard` rendering the honest score card (or the
abstain state) + a per-topic table including **median latency** (S8), behind a
mapper that makes a bare number structurally impossible.

```bash
just test-ts        # dashboard lib.test.ts: 14 pass (incl. honesty-guard cases)
just lint           # svelte-check + tsc clean
```

See it live — start the dev app, then open the page in a browser (the RPC is
served by the in-app server on port 40000, and is now exposed to the frontend):

```bash
ANKI_BASE=/tmp/pgre-dash just run
# then open in any browser:
open http://localhost:40000/speedrun-dashboard
```

On an empty/SM-2 profile it shows the **abstain** card; after the FSRS reviews from
the S2/S3 walkthrough it shows the score card with range, coverage, confidence,
reasons, and the latency column. (There's no Tools-menu entry yet — you reach it by
URL.)

---

## S6 — iOS C-FFI (proves iOS runs the _same_ engine)

```bash
cargo test -p anki-ffi        # 6 pass: round-trip, open+query, 10k-loop, and buildhash parity
mobile/build-xcframework.sh   # builds mobile/AnkiCore.xcframework (device + simulator slices)
```

The parity test asserts the `buildhash()` linked into the FFI equals the desktop
build's (`out/buildhash`) — same engine, not a reimplementation.

---

## S7 — iOS SwiftUI review app (in the Simulator)

`mobile/SpeedrunApp/` opens the bundled PGRE deck and runs a real review loop on the
shared engine via the S6 C-FFI. (Needs the iOS setup from §0.)

```bash
export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"
cd mobile/SpeedrunApp
# build for the simulator (the must-pass bar):
xcodebuild -scheme SpeedrunApp -destination 'platform=iOS Simulator,name=iPhone 17' build CODE_SIGNING_ALLOWED=NO
# automated 20-review check (XCUITest taps Show-Answer + grade x20):
xcodebuild -scheme SpeedrunApp -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: **BUILD SUCCEEDED**, then **TEST SUCCEEDED** (`testTwentyReviews`) — 20
graded answers persist to the app's `Documents/collection.anki2` with nonzero
`taken_millis`, through the shared engine.

By hand: `xcrun simctl boot "iPhone 17"; open -a Simulator`, install the built
`.app` (`xcrun simctl install …`), `xcrun simctl launch net.ankiweb.speedrun`, tap
Show Answer + a grade ≥20×, then open that profile's
`Documents/collection.anki2` in desktop Anki to see updated cards (path via
`xcrun simctl get_app_container "iPhone 17" net.ankiweb.speedrun data`).

> swift-protobuf resolves from its normal SwiftPM remote. In this sandboxed env a
> leftover git config can block the clone; the build wraps the one xcodebuild call
> with `GIT_CONFIG_VALUE_0=all` (no persisted change). On a normal machine that
> isn't needed.

---

## S9 — installer + crash safety

```bash
# installer builds (needs the submodule from §0 + Xcode):
PYTHONPATH=pylib:out/pylib:out/qt:out/qt/tools ANKI_TEST_MODE=1 \
  out/pyenv/bin/pytest -p no:cacheprovider qt/tests/test_installer.py -v      # all pass

# crash safety: SIGKILL the engine mid-write, prove no corruption:
just speedrun-crash-test                                                       # corrupted collections: 0 / 50
```

A packaged `.dmg` + a clean-machine install recording is the manual "proof" step
(the build passing is what's verified automatically here).
