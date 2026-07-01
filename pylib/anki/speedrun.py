# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun PGRE: high-level access to the per-topic mastery / memory score.

Wraps the generated `topic_mastery` backend RPC so callers use
`col.speedrun.topic_mastery(...)` instead of touching `col._backend`
(see docs/language_bridge.md). Passing 0 for any field applies the backend's
documented defaults (mastered_threshold=0.9, review_floor=20, coverage_floor=0.40).
"""

from __future__ import annotations

import anki
import anki.collection
import anki.speedrun_pb2

# public export
TopicMasteryResponse = anki.speedrun_pb2.TopicMasteryResponse


class SpeedrunManager:
    def __init__(self, col: anki.collection.Collection) -> None:
        self.col = col.weakref()

    def topic_mastery(
        self,
        *,
        mastered_threshold: float = 0.0,
        review_floor: int = 0,
        coverage_floor: float = 0.0,
    ) -> TopicMasteryResponse:
        """Per-topic mastery + an honest memory score (or an abstaining result).

        Zero values fall back to the backend defaults. The returned message
        carries either `abstain=True` (with `abstain_reasons`) or a
        `memory_score` plus its Wilson `[score_low, score_high]` range,
        `coverage`, `confidence`, `reasons`, and per-topic `topics`.
        """
        return self.col._backend.topic_mastery(
            mastered_threshold=mastered_threshold,
            review_floor=review_floor,
            coverage_floor=coverage_floor,
        )

    def deck_mastery(
        self, *, mastered_threshold: float = 0.0
    ) -> anki.speedrun_pb2.DeckMasteryResponse:
        """Per-deck mastered-card counts (for the Stats "Mastered" view).

        One row per deck that has >=1 card. Zero applies the default threshold.
        """
        return self.col._backend.deck_mastery(mastered_threshold=mastered_threshold)
