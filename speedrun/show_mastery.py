# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Pretty-print the PGRE topic-mastery / memory score for a collection.

Opens an ``.anki2`` collection and calls the fork-specific
``SpeedrunService.TopicMastery`` RPC, then prints either an honest ABSTAIN
notice (with reasons) or the memory score with its confidence range, coverage,
and a per-topic breakdown.

Run via ``just speedrun-mastery`` (preferred) or::

    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/show_mastery.py \
        --col out/speedrun/work/pgre_main.anki2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from anki.collection import Collection

# Allow running both as ``python speedrun/show_mastery.py`` and ``-m``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Registers ``anki.speedrun_pb2`` on the ``anki`` package so the generated
# backend method can build its request/response messages.
import anki.speedrun_pb2  # noqa: E402,F401

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COL = REPO_ROOT / "out" / "speedrun" / "work" / "pgre_main.anki2"


def _print_topics(topics) -> None:
    header = (
        f"  {'subject':<38}{'total':>6}{'state':>6}"
        f"{'mastered':>9}{'mean R':>8}{'lat ms':>8}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for t in topics:
        print(
            f"  {t.name:<38}{t.total_cards:>6}{t.cards_with_state:>6}"
            f"{t.mastered:>9}{t.mean_retrievability * 100:>7.0f}%"
            f"{t.median_latency_ms:>8}"
        )


def show(col_path: Path) -> int:
    col = Collection(str(col_path))
    try:
        r = col._backend.topic_mastery(
            mastered_threshold=0.0, review_floor=0, coverage_floor=0.0
        )
    finally:
        col.close()

    print(f"Collection: {col_path}")
    print(
        f"Thresholds: mastered>={r.thresholds.mastered_threshold:.2f}  "
        f"review_floor={r.thresholds.review_floor}  "
        f"coverage_floor={r.thresholds.coverage_floor:.0%}"
    )
    print(f"Coverage: {r.coverage:.0%}   Total reviews: {r.total_reviews}")
    print()

    if r.abstain:
        print("ABSTAIN — no memory score shown.")
        print("Reasons:")
        for reason in r.abstain_reasons:
            print(f"  - {reason}")
    else:
        print(
            f"Memory score: {r.memory_score:.0%}  "
            f"[{r.score_low:.0%}, {r.score_high:.0%}]  "
            f"(confidence: {r.confidence})"
        )
        if r.reasons:
            print("Weakest covered subjects:")
            for reason in r.reasons:
                print(f"  - {reason}")

    print()
    _print_topics(r.topics)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--col",
        type=Path,
        default=DEFAULT_COL,
        help="path to an .anki2 collection (default: %(default)s)",
    )
    args = parser.parse_args()

    if not args.col.exists():
        print(f"error: collection not found: {args.col}", file=sys.stderr)
        return 1
    return show(args.col)


if __name__ == "__main__":
    raise SystemExit(main())
