# Categorized PGRE Decks

The 8 source decks in `../anki-decks/` (1,178 notes) re-sorted into the **9
Physics GRE subject areas**. Each `.apkg` imports into Anki as a
`PGRE::<Subject>` deck, with every note also tagged `pgre::<subject_key>`.
Images and card templates are preserved.

| File | Subject | Notes |
|------|---------|------:|
| 01_Classical_Mechanics.apkg | Classical Mechanics | 68 |
| 02_Electromagnetism.apkg | Electromagnetism | 441 |
| 03_Quantum_Mechanics.apkg | Quantum Mechanics | 46 |
| 04_Atomic_Physics.apkg | Atomic Physics | 69 |
| 05_Thermodynamics_Statistical_Mechanics.apkg | Thermodynamics & Statistical Mechanics | 135 |
| 06_Optics_Waves.apkg | Optics & Waves | 215 |
| 07_Specialized_Topics.apkg | Specialized Topics (nuclear/particle/condensed matter/astro) | 178 |
| 08_Special_Relativity.apkg | Special Relativity | 18 |
| 09_Laboratory_Methods.apkg | Laboratory Methods | 7 |
| | **Total** | **1,177** |

(1,177 vs 1,178: one Particle Physics note was a duplicate and merged on import.)

## How the sort was done

Each note was classified by a **keyword classifier** (physics terms → subject)
combined with a **source-deck prior** (a card from the Electromagnetism deck
defaults to Electromagnetism unless its text strongly indicates otherwise). No AI
was used. Tooling: the `anki` library (import/tag/export) + a keyword classifier;
subject keys/names come from [speedrun/taxonomy.py](../speedrun/taxonomy.py).

## Accuracy caveats

- **Single-topic source decks sorted near-perfectly** (Electromagnetism 346/347,
  Optics 88/88, Waves 106/106, Thermodynamics 92/93, Particle 57/57).
- **Mixed decks** (Physics GRE, Physics GRE Equations, Modern Physics) were split
  card-by-card and are the main source of any misclassification.
- **Specialized Topics** doubles as the catch-all for notes with no strong keyword
  match (~71 notes repository-wide), so it may contain some cards that belong
  elsewhere.
- **Laboratory Methods (7)** and **Special Relativity (18)** are genuinely sparse
  in the source material, not an error.
- Overlapping terms (e.g. "angular momentum", "harmonic oscillator" appear in both
  Classical and Quantum) are resolved by keyword weighting + deck prior, so a
  handful of edge cards may land in the neighboring subject.

Treat this as a high-quality first pass; a quick manual skim of the smaller decks
will catch the few ambiguous cards.
