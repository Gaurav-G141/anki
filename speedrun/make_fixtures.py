# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate deterministic PGRE deck fixtures via Anki's Python API.

Outputs ``.colpkg`` collection packages (and working ``.anki2`` files) under
``out/speedrun/`` for use by the desktop dashboard, the iOS app, and the S1/S2
tests (SPECS.md §F). Content is deterministic so re-runs produce equivalent
decks (counts, tags, subjects); only embedded timestamps differ.

Run via ``just speedrun-fixtures`` (preferred) or::

    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/make_fixtures.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from anki.collection import Collection

# Allow running both as ``python speedrun/make_fixtures.py`` and ``-m``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from speedrun import taxonomy  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out" / "speedrun"
WORK_DIR = OUT_DIR / "work"

DECK_ROOT = "PGRE"
CARDS_PER_SUBJECT = 6
#: Fraction of cards (per subject) to review once, to seed revlog history.
REVIEW_FRACTION = 0.5


@dataclass
class FixtureSpec:
    name: str
    subject_keys: list[str]
    cards_per_subject: int = CARDS_PER_SUBJECT
    seed_reviews: bool = True


def _fresh_collection(name: str) -> Collection:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    path = WORK_DIR / f"{name}.anki2"
    for p in (path, path.with_suffix(".media")):
        if p.exists():
            if p.is_dir():
                for child in p.iterdir():
                    child.unlink()
                p.rmdir()
            else:
                p.unlink()
    return Collection(str(path))


def _add_subject_cards(col: Collection, subject: taxonomy.Subject, count: int) -> int:
    """Add ``count`` Basic notes for a subject, tag them, return cards added."""
    notetype = col.models.by_name("Basic")
    assert notetype is not None, "Basic notetype missing"
    deck_id = col.decks.id(taxonomy.deck_name_for(subject.key, DECK_ROOT))
    note_ids = []
    for i in range(count):
        note = col.new_note(notetype)
        note["Front"] = f"[{subject.name}] formula #{i + 1}?"
        note["Back"] = f"{subject.name} answer {i + 1}"
        col.add_note(note, deck_id)
        note_ids.append(note.id)
    col.tags.bulk_add(note_ids, subject.tag)
    return len(note_ids)


def _seed_reviews(col: Collection, fraction: float) -> int:
    """Answer a fraction of due/new cards once to populate the revlog."""
    root_id = col.decks.id(DECK_ROOT)
    col.decks.select(root_id)
    total = col.card_count()
    target = int(total * fraction)
    answered = 0
    while answered < target:
        card = col.sched.getCard()
        if card is None:
            break
        col.sched.answerCard(card, 3)  # "Good"
        answered += 1
    return answered


def build_fixture(spec: FixtureSpec) -> dict:
    col = _fresh_collection(spec.name)
    per_subject: dict[str, int] = {}
    try:
        for key in spec.subject_keys:
            subject = taxonomy.BY_KEY[key]
            per_subject[key] = _add_subject_cards(col, subject, spec.cards_per_subject)
        reviews = _seed_reviews(col, REVIEW_FRACTION) if spec.seed_reviews else 0
        summary = {
            "name": spec.name,
            "notes": col.note_count(),
            "cards": col.card_count(),
            "reviews_seeded": reviews,
            "subjects": per_subject,
            "tags": sorted(t for t in col.tags.all() if t.startswith(taxonomy.TAG_PREFIX)),
        }
    finally:
        # export_collection_package closes the collection.
        colpkg = OUT_DIR / f"{spec.name}.colpkg"
        col.export_collection_package(str(colpkg), include_media=False, legacy=False)
    summary["colpkg"] = str(colpkg.relative_to(REPO_ROOT))
    summary["anki2"] = str((WORK_DIR / f"{spec.name}.anki2").relative_to(REPO_ROOT))
    return summary


def empty_fixture(name: str) -> dict:
    col = _fresh_collection(name)
    try:
        summary = {
            "name": name,
            "notes": col.note_count(),
            "cards": col.card_count(),
            "reviews_seeded": 0,
            "subjects": {},
            "tags": [],
        }
    finally:
        colpkg = OUT_DIR / f"{name}.colpkg"
        col.export_collection_package(str(colpkg), include_media=False, legacy=False)
    summary["colpkg"] = str(colpkg.relative_to(REPO_ROOT))
    summary["anki2"] = str((WORK_DIR / f"{name}.anki2").relative_to(REPO_ROOT))
    return summary


def main() -> int:
    taxonomy.validate()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_keys = [s.key for s in taxonomy.SUBJECTS]
    without_classical = [k for k in all_keys if k != "classical_mechanics"]

    specs = [
        FixtureSpec("pgre_main", all_keys),
        FixtureSpec("pgre_missing_highweight", without_classical),
    ]

    manifest = {"fixtures": [build_fixture(s) for s in specs]}
    manifest["fixtures"].append(empty_fixture("pgre_empty"))

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"\nWrote {len(manifest['fixtures'])} fixtures to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
