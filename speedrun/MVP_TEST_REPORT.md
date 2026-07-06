# Speedrun PGRE — MVP Test Report (independent verification)

Rigorous test cases for the **Wednesday MVP** (per `Speedrun_ … Anki.pdf` §6,
§2, §7, §10), each **independently executed** in this session (not copied from
the compliance doc). Exam: **Physics GRE**.

Legend: ✅ verified here · 🟡 partial / builds-but-manual-artifact · ⏭️ Fri/Sun by
the doc's schedule · 🚧 **deferred to your official iOS build** (not run here).

Date of run: 2026-07-01. Machine: local dev (macOS, debug unless noted).

> **UPDATE 2026-07-05 (Sunday build) — the 🚧/⏭️ items below are now resolved; this
> section records the Wednesday snapshot for the record.** Current state (see
> `COMPREHENSIVE_TEST_REPORT.md`): `just check` green — **570 Rust / 1 skipped**,
> **145 Python**, TS vitest green; the only red is the non-blocking
> `check:complexipy-diff:qt` on **10 pre-existing upstream Anki functions** (0-diff vs
> `main`, not fork code, not a regression). `just bench` 50k p50/p95/p99 **32/33/33 ms**
> (runs 32–104 ms under load, always << budget); `just speedrun-crash-test 50` **0/50**;
> 200K stress **7/7** (205,531 cards). **iOS (W6/W7) is now built**: 12/12 on the
> iPhone 17 simulator, and the device build (`arm64 iphoneos`) packages as
> `installers/SpeedrunApp-iOS-device-unsigned.ipa` — **UNSIGNED** sideload
> (Sideloadly/AltStore), **not** TestFlight (no paid Apple account). This session also
> fixed the **MCQ nucleus** (now a true circle, `qt/aqt/pgre.py`), **AI-grader
> calibration** (rubric guard + grading temperature 0, synced desktop/iOS), and
> **ablation determinism** (fixed SHA-256 offset). Fri/Sun evals (also in the
> comprehensive report): baseline AI **66% (31/47) vs 28%/23%/20%** and paraphrase
> **n=30, 77%→77%, +0% drop** are **real held-out GR9277** measurements; calibration
> (Brier **0.1409** / log-loss **0.4453** / ECE **0.0307**) and the ablation (honest
> null **−1.6%**, 95% CI [−0.115, +0.039] spans 0) are **deterministic SIMULATIONS of a
> synthetic learner** (not real users). Leakage + gen-leakage CLEAN. Still open (honest):
> demo video + proof recordings NOT recorded; iOS unsigned (not TestFlight); no committed
> automated two-device sync-conflict harness; README does not state the give-up rule.

## Commands run + results

| Suite                        | Command                                            | Result                                                                                   |
| ---------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Rust engine change           | `cargo test -p anki speedrun`                      | **18 passed, 0 failed** (1 perf `#[ignore]`d)                                            |
| Rust perf (50k, release)     | `just bench`                                       | **p50 51.8 / p95 53.2 / p99 55.9 ms** (budget 150) ✅                                    |
| Python cross-language        | `pytest pylib/tests/test_speedrun.py`              | **6 passed**                                                                             |
| Qt home/first-run import     | `pytest qt/tests/test_pgre.py`                     | **6 passed**                                                                             |
| TS dashboard + honesty guard | `vitest run routes/speedrun-dashboard/lib.test.ts` | **14 passed**                                                                            |
| Installer builds             | `pytest qt/tests/test_installer.py`                | **27 passed** (26 s)                                                                     |
| Deck fixtures (S1)           | `just speedrun-fixtures && just speedrun-test`     | PASS                                                                                     |
| Honest score / abstain       | `just speedrun-demo`                               | abstain → score `100% [92%,100%] Wilson95`, coverage 100%, confidence, weakest topics ✅ |
| Crash safety (§7g)           | `just speedrun-crash-test 20`                      | **0 / 20 corrupted** ✅                                                                  |
| Shared-engine FFI compiles   | `cargo check -p anki-ffi`                          | **Finished, 0 errors** ✅                                                                |

## MVP requirement matrix (§6 "Due Wednesday")

| #  | Requirement                                            | Verdict | Evidence (this run)                                                                                                                                                                |
| -- | ------------------------------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| W1 | Anki fork builds from source                           | ✅      | pylib+qt built; every suite above ran against the built engine; installer test builds wheels                                                                                       |
| W2 | Rust change end-to-end: diff + ≥3 Rust + 1 Python test | ✅      | 18 Rust + 6 Python passed; `SpeedrunService.TopicMastery`; diff/why-Rust in [RUST_CHANGE.md](RUST_CHANGE.md)                                                                       |
| W3 | Review loop on the exam deck                           | ✅      | PGRE decks import (1,212 notes live); Anki's review loop is the (unchanged) engine path; qt pgre first-run import tested                                                           |
| W4 | Memory model, honest score: range + give-up rule       | ✅      | `speedrun-demo` shows abstain→Wilson-range score; `scored_response_satisfies_honesty_contract`, `give_up_review_floor_boundary`, `missing_high_weight_subject_abstains` all pass   |
| W5 | Installer runs on a clean machine                      | 🟡      | Installer **builds** (27 tests pass). Packaged `.dmg` + clean-machine launch = manual recording                                                                                    |
| W6 | Phone app builds & runs on device/emulator             | 🚧 → ✅ | Not run here on 07-01. **Sunday:** sim 12/12 + device `arm64 iphoneos` build SUCCEEDED → `installers/SpeedrunApp-iOS-device-unsigned.ipa` (unsigned sideload, **not** TestFlight). |
| W7 | Phone loads deck + real review on shared engine        | 🚧 → ✅ | `anki-ffi` compiles; xcframework from same `rslib`. **Sunday:** `testTwentyReviews` (20 grades via shared engine) TEST SUCCEEDED on iPhone 17 sim.                                 |
| W8 | Proof (commit hash, recordings, test results)          | 🟡      | Test results = this report. Recordings/commit-hash = manual                                                                                                                        |

## Cross-cutting rules (§2) & challenges (§7, §10) relevant to MVP

| Item                                                    | Verdict | Evidence                                                                                                     |
| ------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------ |
| Real change in Rust core (§2, §7a)                      | ✅      | `rslib/src/speedrun/` RPC; 18 Rust tests                                                                     |
| Undo works / no corruption (§7a)                        | ✅      | `rpc_is_read_only_and_preserves_integrity` (100× calls, undo+counts+`check_database` unchanged) + crash 0/20 |
| Coverage map + abstain on missing section (§7c)         | ✅      | `missing_high_weight_subject_abstains` + fixture                                                             |
| Give-up / refuse a score without data (§2)              | ✅      | `empty_collection_abstains`; demo State A abstains                                                           |
| Three scores, each a range (§2, §4)                     | 🟡      | **Memory ✅** (range+abstain); Performance/Readiness stubbed → ⏭️ Fri/Sun                                     |
| Share one engine, both apps (§3)                        | 🟡      | Engine shared (`anki-ffi` compiles, xcframework from same core); **two-way sync ⏭️ Friday**                   |
| One-command benchmark (§7h)                             | ✅      | `just bench` → p50/p95/p99 on 50k                                                                            |
| Dashboard first-load p95 < 1 s / refresh < 500 ms (§10) | ✅      | RPC p95 ≈ 53 ms release                                                                                      |
| Zero corrupted collections in crash test (§10)          | ✅      | 0/20 (recipe supports 50)                                                                                    |
| AGPL-3.0 + credit Anki (§2)                             | ✅      | license unchanged; README states exam + credit                                                               |
| No AI in Wednesday build (§6)                           | ✅      | no model calls anywhere in MVP paths                                                                         |

## Honest gaps / not verified here

- **iOS build & on-device/simulator review (W6, W7): NOT run in this 07-01 session.**
  Only static checks here — the Xcode project, prebuilt `AnkiCore.xcframework` (device +
  simulator), and a clean `cargo check -p anki-ffi`. **Closed on 2026-07-05:** sim
  12/12 (incl. `testTwentyReviews`), device `arm64 iphoneos` build SUCCEEDED →
  `installers/SpeedrunApp-iOS-device-unsigned.ipa` (unsigned sideload, not TestFlight —
  no paid Apple account).
- **Installer (W5): builds, not packaged/installed here.** A `.dmg` on a clean
  machine is a manual/recording artifact.
- **Full `just check` not re-run in the 07-01 session** — I ran the targeted MVP
  suites instead (all green). **On 2026-07-05 `just check` is green** (570 Rust / 1
  skipped, 145 Python, TS vitest green); its only red is the non-blocking
  `check:complexipy-diff:qt` on 10 pre-existing upstream Anki functions (0-diff vs
  `main`, not fork code).
- **Button-press ack & next-card p95 (§10)** not separately profiled — those are
  Anki's unchanged review path; only the new dashboard RPC was benchmarked.
- Fri/Sun items — two-way sync (§7b), AI + its checks (§7d/e/f), the ablation
  experiment (§8), held-out score calibration (§9), Performance/Readiness models
  — are **out of Wednesday scope** by the doc's own schedule.

## Bottom line

Every **Wednesday MVP requirement that can be checked without packaging or an
Xcode build passed** when run independently: the Rust engine change (18 tests),
Python bridge (6), Qt first-run import (6), TS honesty-guarded dashboard (14),
installer build (27), fixtures, the honest abstain→score behavior, the 50k
benchmark (p95 ≈ 53 ms), crash safety (0/20), and the shared-engine FFI compile.
The remaining Wednesday items are **your official iOS build** (W6/W7) and the
**manual proof artifacts** (packaged installer run + recordings) — not code gaps.
