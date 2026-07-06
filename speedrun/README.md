# Speedrun (fork-specific tooling)

Project-specific tooling for the Speedrun Physics-GRE build. See [PRD.md](../PRD.md)
and [SPECS.md](../SPECS.md) at the repo root for the full plan.

This package builds **on top of Anki's public Python API** (the `anki` library)
and the engine change planned in `rslib/src/speedrun/` (SPECS.md S2). It does not
touch engine internals, so it stays decoupled and easy to merge with upstream.

## Contents

| File                        | Purpose                                                                                                                                                                                   |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `taxonomy.py`               | Canonical PGRE subjects, exam weights, tag names, subscore buckets. Single source of truth (the Rust engine change mirrors it).                                                           |
| `make_fixtures.py`          | Generates deterministic tagged decks (`.colpkg`) for tests/demos.                                                                                                                         |
| `verify_fixtures.py`        | S1 test harness (SPECS.md S1-T01..T04); prints a JSON report, exits non-zero on failure.                                                                                                  |
| `tag_deck.py`               | Re-tags a real imported `.apkg` into the taxonomy via an explicit query→subject map (no AI).                                                                                              |
| `calibration_eval.py`       | Memory-model calibration (Brier / log-loss / ECE + reliability). Deterministic seeded **simulation** of a synthetic learner.                                                              |
| `ablation.py`               | Three-arm Speed-Recall ablation (full / feature-off / plain-Anki), mastered-per-minute ± range. Deterministic **simulation** (SHA-256 offset, reproducible after the PYTHONHASHSEED fix). |
| `baseline_eval.py`          | Blind GPT-4o solver vs keyword/vector baselines on the held-out split (live; `--dry-run` for baselines-only).                                                                             |
| `paraphrase_eval.py`        | AI accuracy on original vs reworded held-out questions (generalization, not memorization); live, `--dry-run` offline.                                                                     |
| `andy_eval.py`              | Scores the "Explain with Andy" tutor for correctness + conciseness; live, `--dry-run` offline.                                                                                            |
| `leakage_check.py`          | Dev/held-out split disjointness + near-dup (Jaccard) + no exam-text-in-prompts checks (spec 7e).                                                                                          |
| `gen_leakage_check.py`      | Leakage check for generated items (novel <0.6 Jaccard vs real; reworded within [0.15, 0.75) of seed).                                                                                     |
| `gen_eval.py`               | Regenerates + validates the AI card bank via 3-solver consensus + single-correct + soundness + novelty gates (spec 7f).                                                                   |
| `heuristic_eval.py`         | Stage-1 optimal-approach-key eval for the FRQ Heuristic Coach.                                                                                                                            |
| `crash_test.py`             | SIGKILL-mid-write crash-safety harness (S9); backs `just speedrun-crash-test`.                                                                                                            |
| `large_deck_stress_test.py` | Stress + speed test on a large deck; times every hot path vs PRD targets (backs `just stress`).                                                                                           |

## Commands (wired into `just`)

```bash
just speedrun-fixtures   # build pylib if needed, then write fixtures to out/speedrun/
just speedrun-test       # verify the fixtures (S1 gate)
```

All recipes run under the built dev environment (`out/pyenv` + `PYTHONPATH=out/pylib`).

### Evals & tests (Friday/Sunday)

```bash
# Deterministic simulations (no OpenAI key needed):
just calibrate            # Brier / log-loss / ECE + reliability chart (simulated learner)
just ablation             # 3-arm Speed-Recall ablation, mastered/min ± CI (reproducible sim)

# Live evals on real held-out GR9277 items (need an OpenAI key; add --dry-run for offline):
just baseline-eval        # blind GPT-4o solver vs keyword/vector baselines
just paraphrase-eval      # original vs reworded accuracy (generalization)
just andy-eval            # "Explain with Andy" tutor correctness + conciseness

# Performance / safety / scale:
just bench                # topic_mastery scan p50/p95/p99 on a 50k deck (release)
just speedrun-crash-test  # SIGKILL mid-write N times, prove 0 corruption
just stress               # stress + speed-test the shared engine on a large deck

# Leakage / generated-bank integrity (run the scripts directly):
out/pyenv/bin/python speedrun/leakage_check.py       # dev/held-out disjoint, no near-dups, no exam text in prompts
out/pyenv/bin/python speedrun/gen_leakage_check.py   # generated items: novelty + reworded-distance bounds
out/pyenv/bin/python speedrun/gen_eval.py            # regenerate + validate the AI card bank (consensus/soundness/novelty gates)
```

> **Honesty note.** `calibrate` and `ablation` are **deterministic simulations of a
> synthetic learner** (no real multi-month user logs exist) — phrase their outputs as
> simulated, not "measured on real users." `bench`, `baseline-eval`, and
> `paraphrase-eval` use **real held-out GR9277 items** and are genuinely measured.

## Outputs

Generated artifacts go to **`out/speedrun/`** (git-ignored), keeping the tracked
tree clean:

- `pgre_main.colpkg` — all 9 subjects, tagged + seeded reviews (the demo deck).
- `pgre_missing_highweight.colpkg` — omits Classical Mechanics (a ≥10% subject);
  drives the S2 "abstain when a high-weight section is missing" test.
- `pgre_empty.colpkg` — empty collection; drives the abstain/give-up path.
- `manifest.json` — per-fixture counts, subjects, tags, and paths.

## Tagging convention

Notes are tagged `pgre::<subject_key>` (e.g. `pgre::classical_mechanics`). Each
note carries **exactly one** subject tag (mastery aggregation assumes disjoint
subjects). Subject keys, names, and weights live in `taxonomy.py`.

## Bringing your own deck

```bash
PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/tag_deck.py \
    --apkg path/to/public_pgre.apkg --map map.json \
    --out out/speedrun/pgre_tagged.colpkg --strip
```

where `map.json` maps Anki search queries to subject keys, e.g.
`{"deck:Mechanics": "classical_mechanics"}`.
