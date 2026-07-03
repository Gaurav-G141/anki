# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Seed a 'dummy account' collection with MODERATE progress, for demoing the
three honest scores (Memory / Performance / Readiness) from a real learner's
perspective.

It builds a collection at ``--out`` with all 9 PGRE subjects covered, FSRS
memory-state on a gradient of cards (controls mastered% / Memory), and graded
revlog rows (controls accuracy / Performance -> Readiness). No live study run is
needed: per demo-profile-seeding, the mastery reports read ``card.memory_state``
+ ``last_review_time`` directly, and ``total_reviews``/accuracy come from revlog
(``ease`` = grade, ``time`` = ms, ``type`` = review kind).

After building it prints the three scores and asserts none abstains — so running
this IS the end-to-end testcase against the dummy account.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "out/pylib"))

# Import order matters: anki.collection before anki.cards (circular import).
import anki.collection  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.cards import FSRSMemoryState  # noqa: E402
import anki.lang  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "speedrun"))
import taxonomy  # noqa: E402  (fork-specific PGRE subject list)

anki.lang.set_lang("en")

DAY = 86_400


def build(path: str, cards_per: int, reviews_per: int) -> Collection:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    col = Collection(path)
    basic = col.models.by_name("Basic")
    assert basic is not None
    now = int(time.time())
    rev_id = now * 1000  # unique, increasing revlog ids

    n_subjects = len(taxonomy.SUBJECTS)
    for si, subject in enumerate(taxonomy.SUBJECTS):
        # Gradients across subjects: strongest first, weakest last.
        frac = si / max(n_subjects - 1, 1)
        mastered_frac = 0.85 - 0.55 * frac  # 0.85 -> 0.30
        correct_frac = 0.90 - 0.35 * frac  # 0.90 -> 0.55

        deck_id = col.decks.id(f"PGRE::{subject.name}")
        note_ids = []
        cids = []
        for i in range(cards_per):
            note = col.new_note(basic)
            note["Front"] = f"[{subject.key}] q{i}"
            note["Back"] = f"a{i}"
            col.add_note(note, deck_id)
            note_ids.append(note.id)
            cids.append(note.card_ids()[0])
        col.tags.bulk_add(note_ids, subject.tag)

        n_mastered = round(cards_per * mastered_frac)
        revlog_rows = []
        for idx, cid in enumerate(cids):
            mastered = idx < n_mastered
            card = col.get_card(cid)
            if mastered:
                card.memory_state = FSRSMemoryState(stability=200.0, difficulty=4.0)
                card.last_review_time = now - 10 * DAY  # recent -> R high
            else:
                card.memory_state = FSRSMemoryState(stability=20.0, difficulty=7.0)
                card.last_review_time = now - 220 * DAY  # long ago -> R low
            col.update_card(card, skip_undo_entry=True)

            # Graded review history: `correct_frac` of reviews answered Good(3),
            # the rest Again(1). Drives Performance accuracy.
            n_correct = round(reviews_per * correct_frac)
            for r in range(reviews_per):
                rev_id += 1
                button = 3 if r < n_correct else 1
                revlog_rows.append(
                    (
                        rev_id,           # id (unique ms)
                        cid,              # cid
                        0,                # usn
                        button,           # ease = grade
                        0,                # ivl
                        0,                # lastIvl
                        0,                # factor
                        4000 + (r % 5) * 1200,  # time (ms taken)
                        1,                # type = review
                    )
                )
        col.db.executemany(
            "insert into revlog (id,cid,usn,ease,ivl,lastIvl,factor,time,type) "
            "values (?,?,?,?,?,?,?,?,?)",
            revlog_rows,
        )

    # Mark the fork's first-run bundled-deck import as already done, so opening this
    # collection in the desktop app does NOT add ~166 un-mastered formula cards that
    # would dilute the seeded scores (see qt/aqt/pgre.py maybe_import_default_decks).
    col.set_config("pgreDefaultDecksImported", True)

    # Bump the collection mod stamp (raw) so a later sync sees the seeded state.
    col.db.execute("update col set mod = ?", int(time.time() * 1000))
    return col


def verify(col: Collection) -> bool:
    r = col.speedrun.topic_mastery()
    print("\n=== Dummy account — three scores ===")
    print(f"cards={col.card_count()}  reviews={col.db.scalar('select count(*) from revlog')}"
          f"  coverage={r.coverage * 100:.0f}%")
    ok = True

    def line(name, abstain, score, low, high, conf, scaled=False):
        nonlocal ok
        if abstain:
            ok = False
            print(f"  {name:12} ABSTAIN (unexpected)")
        elif scaled:
            print(f"  {name:12} {score:.0f}   range {low:.0f}–{high:.0f}   ({conf})")
        else:
            print(f"  {name:12} {score * 100:.0f}%  range {low * 100:.0f}%–{high * 100:.0f}%   ({conf})")

    line("Memory", r.abstain, r.memory_score, r.score_low, r.score_high, r.confidence)
    line("Performance", r.performance_abstain, r.performance_score,
         r.performance_low, r.performance_high, r.performance_confidence)
    line("Readiness", r.readiness_abstain, r.readiness_score,
         r.readiness_low, r.readiness_high, r.readiness_confidence, scaled=True)

    assert not r.abstain, "Memory should not abstain"
    assert not r.performance_abstain, "Performance should not abstain"
    assert not r.readiness_abstain, "Readiness should not abstain"
    assert r.score_low <= r.memory_score <= r.score_high
    assert r.performance_low <= r.performance_score <= r.performance_high
    assert 200 <= r.readiness_score <= 990
    assert r.readiness_low <= r.readiness_score <= r.readiness_high
    assert r.readiness_score % 10 == 0
    print("  -> all three scores present, ranged, non-abstaining  ✅")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="collection.anki2 path to create")
    ap.add_argument("--cards-per", type=int, default=14)
    ap.add_argument("--reviews-per", type=int, default=6)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    col = build(args.out, args.cards_per, args.reviews_per)
    verify(col)
    col.close()
    print(f"\nSeeded collection: {args.out}")


if __name__ == "__main__":
    main()
