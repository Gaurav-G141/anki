# Bundled PGRE decks — sources & licensing

These `.apkg` files ship with the Speedrun (Physics GRE) fork and are
auto-imported on first run (see `qt/aqt/pgre.py`). This note records where each
came from so licensing can be confirmed **before any public release**.

> ⚠️ **Action before publishing:** the 9 subject decks are derived from
> third-party community decks whose licenses are not confirmed here. Verify each
> is redistributable (or replace with self-authored / clearly-licensed content)
> before distributing the app publicly. The app's own code is AGPL-3.0-or-later;
> that license does **not** cover bundled third-party deck content.

## Files

| File                                                         | Contents                                                                    | Source / provenance                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------ | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `01_Classical_Mechanics.apkg` … `09_Laboratory_Methods.apkg` | The 9 PGRE subject decks (cards re-sorted by topic)                         | Built by importing and re-categorizing **third-party community decks** downloaded from AnkiWeb (e.g. "Electromagnetism / Optics / Modern Physics – CBSE Class XII", "Physics – Particle Physics", "Physics – Waves", "Physics GRE", "Physics GRE Equations", and "Quantum Physics – PHYS 214, UIUC"). Original authors/licenses as listed on their AnkiWeb pages. **Licenses unconfirmed — verify before redistribution.** |
| `Speed_Recall_Formulas.apkg`                                 | 166 "Formula for X" → formula cards, grouped into `Speed Recall::<subject>` | Formula list assembled from the equation index of _Conquering the Physics GRE_ (Kahn & Anderson). The **formulas themselves are facts** (not copyrightable) and card fronts use standard physics names; only the equations (facts) are reproduced, not the book's prose. Still, review before public release.                                                                                                              |

## Notes

- Only these files under `qt/aqt/data/decks/` ship with the app. The repo's
  `anki-decks/` and `categorized decks/` folders (raw downloads + intermediate
  outputs) are git-ignored and **not** distributed.
- The source textbook PDF is intentionally **not** committed to the repo.
