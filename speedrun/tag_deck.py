# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Re-tag an imported public PGRE deck into the canonical taxonomy.

Wednesday is AI-free, so subject assignment is driven by an explicit mapping
file rather than a model. Given an ``.apkg`` and a JSON map of
``{anki_search_query: subject_key}``, this imports the deck, applies the
matching ``pgre::<subject>`` tag to each note, optionally strips any pre-existing
``pgre::`` subject tags first, and exports a tagged ``.colpkg``.

Example map (``map.json``)::

    {"deck:\\"Physics::Mechanics\\"": "classical_mechanics",
     "tag:E&M": "electromagnetism"}

Usage::

    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/tag_deck.py \\
        --apkg deck.apkg --map map.json --out out/speedrun/pgre_tagged.colpkg
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anki.collection import Collection, ImportAnkiPackageRequest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from speedrun import taxonomy  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _strip_subject_tags(col: Collection) -> None:
    for subject in taxonomy.SUBJECTS:
        nids = col.find_notes(f'"tag:{subject.tag}"')
        if nids:
            col.tags.bulk_remove(list(nids), subject.tag)


def tag_deck(apkg: Path, mapping: dict[str, str], out: Path, strip: bool) -> dict:
    work = REPO_ROOT / "out" / "speedrun" / "work" / "tag_deck.anki2"
    work.parent.mkdir(parents=True, exist_ok=True)
    if work.exists():
        work.unlink()

    col = Collection(str(work))
    summary: dict = {"applied": {}, "unmatched_queries": []}
    try:
        col.import_anki_package(ImportAnkiPackageRequest(package_path=str(apkg)))
        if strip:
            _strip_subject_tags(col)
        for query, subject_key in mapping.items():
            if subject_key not in taxonomy.BY_KEY:
                raise SystemExit(f"unknown subject key: {subject_key!r}")
            tag = taxonomy.BY_KEY[subject_key].tag
            nids = list(col.find_notes(query))
            if not nids:
                summary["unmatched_queries"].append(query)
                continue
            col.tags.bulk_add(nids, tag)
            summary["applied"][query] = {"subject": subject_key, "notes": len(nids)}
        # Report notes still missing a subject tag (need mapping coverage).
        subject_tags = {s.tag for s in taxonomy.SUBJECTS}
        untagged = sum(
            1
            for nid in col.find_notes("")
            if not (set(col.get_note(nid).tags) & subject_tags)
        )
        summary["notes_without_subject_tag"] = untagged
        summary["total_notes"] = col.note_count()
    finally:
        out.parent.mkdir(parents=True, exist_ok=True)
        col.export_collection_package(str(out), include_media=True, legacy=False)
    summary["out"] = str(out)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Tag a PGRE .apkg into the taxonomy.")
    ap.add_argument("--apkg", required=True, type=Path)
    ap.add_argument("--map", required=True, type=Path, help="JSON: {query: subject_key}")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--strip", action="store_true", help="remove existing pgre:: subject tags first")
    args = ap.parse_args()

    mapping = json.loads(args.map.read_text())
    summary = tag_deck(args.apkg, mapping, args.out, args.strip)
    print(json.dumps(summary, indent=2))
    if summary["notes_without_subject_tag"] > 0:
        print(
            f"WARNING: {summary['notes_without_subject_tag']} notes have no subject tag "
            "- extend your map for full coverage.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
