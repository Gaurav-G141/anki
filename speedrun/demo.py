# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""One-command demo of the memory model + honest score + give-up rule.

Shows the SpeedrunService.TopicMastery RPC end to end on a real collection:

  1. STATE A — before any FSRS reviews: the give-up rule fires, so the app
     ABSTAINS (no score) and says exactly what's missing.
  2. STATE B — after a short FSRS study session (real reviews → real FSRS memory
     state): a real memory score with a Wilson 95% range, coverage, a "how sure"
     confidence label, weakest-topic reasons, and a per-topic table.

It writes a reusable scored collection to out/speedrun/work/pgre_scored.anki2
(+ .colpkg for importing into the desktop app to see the dashboard). Run via
`just speedrun-demo`.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from anki.collection import Collection

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED = REPO_ROOT / "out" / "speedrun" / "work" / "pgre_main.anki2"
SCORED = REPO_ROOT / "out" / "speedrun" / "work" / "pgre_scored.anki2"
SCORED_COLPKG = REPO_ROOT / "out" / "speedrun" / "pgre_scored.colpkg"
REVIEW_TARGET = 300  # safety cap; the loop stops when the queue is exhausted


def _print_card(col: Collection, header: str) -> None:
    r = col.speedrun.topic_mastery()
    print(f"\n=== {header} ===")
    print(
        f"thresholds: mastered>={r.thresholds.mastered_threshold:.2f}  "
        f"review_floor={r.thresholds.review_floor}  "
        f"coverage_floor={r.thresholds.coverage_floor:.0%}"
    )
    print(f"coverage: {r.coverage:.0%}   total graded reviews: {r.total_reviews}")
    if r.abstain:
        print("\nABSTAIN — no memory score shown (the give-up rule). Reasons:")
        for reason in r.abstain_reasons:
            print(f"  - {reason}")
    else:
        print(
            f"\nMEMORY SCORE: {r.memory_score:.0%}   "
            f"range [{r.score_low:.0%}, {r.score_high:.0%}] (Wilson 95%)   "
            f"confidence: {r.confidence}"
        )
        print("weakest topics:")
        for reason in r.reasons:
            print(f"  - {reason}")
    print(f"\n  {'subject':<38}{'cards':>6}{'state':>6}{'mastered':>9}{'mean R':>8}{'lat ms':>8}")
    print(f"  {'-' * 74}")
    for t in r.topics:
        print(
            f"  {t.name:<38}{t.total_cards:>6}{t.cards_with_state:>6}"
            f"{t.mastered:>9}{t.mean_retrievability:>7.0%}{t.median_latency_ms:>8}"
        )


def main() -> int:
    if not SEED.exists():
        print("ERROR: run `just speedrun-fixtures` first.", file=sys.stderr)
        return 2
    SCORED.parent.mkdir(parents=True, exist_ok=True)
    for p in (SCORED, SCORED.with_suffix(".media")):
        if p.exists():
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copy(SEED, SCORED)

    col = Collection(str(SCORED))
    try:
        # STATE A: honest abstain (no FSRS memory state yet).
        _print_card(col, "STATE A — before FSRS reviews (give-up rule active)")

        # Do a real FSRS study session so the engine computes memory state.
        col.set_config("fsrs", True)
        # Raise the daily new/review limits so every subject gets introduced
        # (otherwise the default 20-new/day caps us to a few subjects).
        try:
            conf = col.decks.config_dict_for_deck_id(col.decks.id("PGRE"))
            conf["new"]["perDay"] = 1000
            conf["rev"]["perDay"] = 1000
            col.decks.save(conf)
        except Exception:
            pass  # demo still works with default limits, just fewer cards
        col.decks.select(col.decks.id("PGRE"))
        reviewed = 0
        while reviewed < REVIEW_TARGET:
            card = col.sched.getCard()
            if card is None:
                break
            # "Easy" graduates a new card immediately, so FSRS memory state is
            # written for it (vs "Good", which leaves it cycling in learning).
            col.sched.answerCard(card, 4)
            reviewed += 1
        print(f"\n[studied {reviewed} cards with FSRS enabled]")

        # STATE B: a real, honest score.
        _print_card(col, "STATE B — after a study session (real honest score)")
    finally:
        col.export_collection_package(str(SCORED_COLPKG), include_media=False, legacy=False)

    print(f"\nScored collection saved to {SCORED.relative_to(REPO_ROOT)}")
    print(f"  re-view the card any time:  just speedrun-mastery col={SCORED.relative_to(REPO_ROOT)}")
    print(f"  dashboard: import {SCORED_COLPKG.relative_to(REPO_ROOT)} into a throwaway profile,")
    print("             then open http://localhost:40000/speedrun-dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
