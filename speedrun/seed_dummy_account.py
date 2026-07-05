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
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "out/pylib"))

# Import order matters: anki.collection before anki.cards (circular import).
import anki.collection  # noqa: E402
from anki.collection import Collection  # noqa: E402
from anki.cards import FSRSMemoryState  # noqa: E402
from anki.consts import CARD_TYPE_REV, QUEUE_TYPE_REV  # noqa: E402
import anki.lang  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "speedrun"))
import taxonomy  # noqa: E402  (fork-specific PGRE subject list)

anki.lang.set_lang("en")

DAY = 86_400

#: Historic spacing ladder (days between successive reviews of one card, oldest→
#: newest), roughly FSRS-shaped. Used to lay a card's reviews back through time so
#: the Stats graphs show real study sessions instead of one "today" spike.
_SPACING_LADDER = (1, 3, 7, 14, 30, 60, 120, 200)


def _review_history(
    rng: random.Random,
    mastered: bool,
    correct_frac: float,
    reviews_per: int,
    last_day_ago: int,
    final_ivl: int,
) -> list[tuple[int, int, int, int]]:
    """Synthesize one card's realistic review history (oldest first).

    Returns ``(day_ago, button, ivl_after, revlog_type)`` rows walking a spaced-
    repetition ladder up to the card's last review (``last_day_ago`` days ago).
    Mastered cards get more reps and mostly-Good grades; weaker cards fewer and
    more Again/Hard early on — so reviews/day, the calendar heatmap and the
    retention graph all look like genuine daily study."""
    n = reviews_per + (rng.randint(2, 6) if mastered else rng.randint(-1, 1))
    n = max(1, n)
    # place reviews backward from the last one, with growing historic gaps
    days = [last_day_ago]
    d = last_day_ago
    for k in range(n - 1):
        d += _SPACING_LADDER[min(k, len(_SPACING_LADDER) - 1)]
        days.append(d)
    days.reverse()  # oldest first
    n_wrong = n - round(n * correct_frac)
    rows: list[tuple[int, int, int, int]] = []
    for i, day_ago in enumerate(days):
        if i < n_wrong:
            button = rng.choice([1, 2])  # Again / Hard while still learning
            rtype = 0 if i == 0 else 2  # first exposure = learn, later miss = relearn
        else:
            button = 3 if rng.random() < 0.82 else 4  # mostly Good, some Easy
            rtype = 1  # review
        ivl_after = (
            _SPACING_LADDER[min(i, len(_SPACING_LADDER) - 1)]
            if i < n - 1
            else final_ivl
        )
        rows.append((day_ago, button, ivl_after, rtype))
    return rows


def _import_bundled_decks(col: Collection, deck_dir: str) -> None:
    """Import the real bundled PGRE subject decks (LaTeX formula cards, already
    tagged ``pgre::<key>``) so the dummy account has genuine content, not
    placeholders. Imports every ``*.apkg`` in ``deck_dir``."""
    import glob

    from anki.collection import ImportAnkiPackageRequest

    apkgs = sorted(glob.glob(os.path.join(deck_dir, "*.apkg")))
    if not apkgs:
        raise SystemExit(
            f"no .apkg decks in {deck_dir}. Run `just build` first, or pass "
            f"--deck-dir pointing at the bundled decks."
        )
    for p in apkgs:
        col.import_anki_package(ImportAnkiPackageRequest(package_path=p))


def build(path: str, reviews_per: int, deck_dir: str) -> Collection:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    col = Collection(path)
    now = int(time.time())
    today = col.sched.today  # scheduler day number, for review-card due dates
    rng = random.Random(20260705)  # deterministic -> reproducible dummy
    used_ids: set[int] = set()  # revlog ids must be unique (ms primary key)

    _import_bundled_decks(col, deck_dir)

    n_subjects = len(taxonomy.SUBJECTS)
    for si, subject in enumerate(taxonomy.SUBJECTS):
        # Gradients across subjects: strongest first, weakest last. Kept in a
        # realistic "good progress" band so every area lands ~50-72% mastered
        # with confident, non-abstaining scores.
        frac = si / max(n_subjects - 1, 1)
        mastered_frac = 0.72 - 0.22 * frac  # 0.72 -> 0.50
        correct_frac = 0.88 - 0.20 * frac  # 0.88 -> 0.68

        # Cards in this subject's bundled deck (incl. subdecks). Seeding by DECK
        # (not tag) keeps the manifold gradient exact: aqt/pgre._deck_mastery counts
        # ivl-mature cards per deck, so the mastered fraction we set here == the
        # mastery the home screen colours with. The deck cards are pgre-tagged, so
        # the tag-scanning mastery RPC (dashboard) sees the same set.
        cids = list(col.find_cards(f'deck:"PGRE::{subject.name}"'))
        if not cids:
            continue

        n_mastered = round(len(cids) * mastered_frac)
        revlog_rows = []
        for idx, cid in enumerate(cids):
            mastered = idx < n_mastered
            card = col.get_card(cid)
            # A real reviewed card, so BOTH mastery signals light up:
            #  - FSRS memory_state drives the dashboard Memory/mastery score;
            #  - the card interval (ivl) drives the manifold home-screen red->green
            #    colouring (aqt/pgre._deck_mastery counts cards with ivl >= 21 as
            #    mature). Without ivl the manifold stays all-red despite the scores.
            # last_review is placed so the *history* below lands on real days:
            # mastered cards reviewed within the last ~2 weeks (a dense recent
            # streak, R high); weaker cards a few months back (an older tail that
            # has since decayed, R low) — this keeps the Memory gradient intact.
            card.type = CARD_TYPE_REV
            card.queue = QUEUE_TYPE_REV
            if mastered:
                last_day_ago = rng.randint(0, 16)
                card.memory_state = FSRSMemoryState(stability=200.0, difficulty=4.0)
                card.ivl = 90  # mature (>= 21d) -> greens the spike
                card.due = today + rng.randint(5, 90)  # spread -> real forecast
            else:
                last_day_ago = rng.randint(170, 250)
                card.memory_state = FSRSMemoryState(stability=20.0, difficulty=7.0)
                card.ivl = 5  # immature (< 21d) -> spike stays red
                card.due = today + rng.randint(0, 3)
            card.last_review_time = now - last_day_ago * DAY
            col.update_card(card, skip_undo_entry=True)

            # Spread this card's graded reviews across real days: drives the Stats
            # reviews/day + calendar + retention graphs, and Performance accuracy.
            for day_ago, button, ivl_after, rtype in _review_history(
                rng, mastered, correct_frac, reviews_per, last_day_ago, card.ivl
            ):
                secs_ago = day_ago * DAY - rng.randint(0, DAY - 1)  # a time that day
                rid = (now - secs_ago) * 1000 + rng.randint(0, 999)
                while rid in used_ids:
                    rid += 1
                used_ids.add(rid)
                revlog_rows.append(
                    (
                        rid,  # id (unique ms = review time)
                        cid,  # cid
                        0,  # usn
                        button,  # ease = grade
                        ivl_after,  # ivl after this review
                        0,  # lastIvl
                        2500,  # factor
                        3000 + rng.randint(0, 8000),  # time (ms taken)
                        rtype,  # 0 learn / 1 review / 2 relearn
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
    print(
        f"cards={col.card_count()}  reviews={col.db.scalar('select count(*) from revlog')}"
        f"  coverage={r.coverage * 100:.0f}%"
    )
    ok = True

    def line(name, abstain, score, low, high, conf, scaled=False):
        nonlocal ok
        if abstain:
            ok = False
            print(f"  {name:12} ABSTAIN (unexpected)")
        elif scaled:
            print(f"  {name:12} {score:.0f}   range {low:.0f}–{high:.0f}   ({conf})")
        else:
            print(
                f"  {name:12} {score * 100:.0f}%  range {low * 100:.0f}%–{high * 100:.0f}%   ({conf})"
            )

    line("Memory", r.abstain, r.memory_score, r.score_low, r.score_high, r.confidence)
    line(
        "Performance",
        r.performance_abstain,
        r.performance_score,
        r.performance_low,
        r.performance_high,
        r.performance_confidence,
    )
    line(
        "Readiness",
        r.readiness_abstain,
        r.readiness_score,
        r.readiness_low,
        r.readiness_high,
        r.readiness_confidence,
        scaled=True,
    )

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
    ap.add_argument(
        "--reviews-per",
        type=int,
        default=3,
        help="graded reviews to synthesize per card (drives Performance)",
    )
    ap.add_argument(
        "--deck-dir",
        default=os.path.join(REPO, "out/qt/_aqt/data/decks"),
        help="folder with the bundled *.apkg subject decks",
    )
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    col = build(args.out, args.reviews_per, args.deck_dir)
    verify(col)
    col.close()
    print(f"\nSeeded collection: {args.out}")


if __name__ == "__main__":
    main()
