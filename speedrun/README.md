# Speedrun (fork-specific tooling)

Project-specific tooling for the Speedrun Physics-GRE build. See [PRD.md](../PRD.md)
and [SPECS.md](../SPECS.md) at the repo root for the full plan.

This package builds **on top of Anki's public Python API** (the `anki` library)
and the engine change planned in `rslib/src/speedrun/` (SPECS.md S2). It does not
touch engine internals, so it stays decoupled and easy to merge with upstream.

## Contents

| File                 | Purpose                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `taxonomy.py`        | Canonical PGRE subjects, exam weights, tag names, subscore buckets. Single source of truth (the Rust engine change mirrors it). |
| `make_fixtures.py`   | Generates deterministic tagged decks (`.colpkg`) for tests/demos.                                                               |
| `verify_fixtures.py` | S1 test harness (SPECS.md S1-T01..T04); prints a JSON report, exits non-zero on failure.                                        |
| `tag_deck.py`        | Re-tags a real imported `.apkg` into the taxonomy via an explicit query→subject map (no AI).                                    |

## Commands (wired into `just`)

```bash
just speedrun-fixtures   # build pylib if needed, then write fixtures to out/speedrun/
just speedrun-test       # verify the fixtures (S1 gate)
```

Both run under the built dev environment (`out/pyenv` + `PYTHONPATH=out/pylib`).

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
