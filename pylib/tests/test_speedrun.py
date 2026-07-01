# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Cross-language tests for the fork-specific ``SpeedrunService.TopicMastery`` RPC.

These exercise the generated Python binding end-to-end against the Rust
backend, verifying the honest-abstain contract, threshold plumbing, and the
shape of the response (see ``proto/anki/speedrun.proto`` and
``rslib/src/speedrun/``).
"""

from __future__ import annotations

# Importing the generated protobuf module registers ``anki.speedrun_pb2`` as an
# attribute of the ``anki`` package, which the generated backend method needs.
import anki.speedrun_pb2  # noqa: F401
from tests.shared import getEmptyCol

#: PGRE subject keys, mirroring ``speedrun/taxonomy.py`` (kept local so the test
#: has no dependency on the fork-specific ``speedrun`` package).
SUBJECT_KEYS = [
    "classical_mechanics",
    "electromagnetism",
    "quantum_mechanics",
    "atomic_physics",
    "thermo_stat_mech",
    "optics_waves",
    "specialized_topics",
    "special_relativity",
    "lab_methods",
]


def _topic_mastery(col, *, mastered_threshold=0.0, review_floor=0, coverage_floor=0.0):
    """Call the RPC. Zero values let the backend apply its documented defaults."""
    return col._backend.topic_mastery(
        mastered_threshold=mastered_threshold,
        review_floor=review_floor,
        coverage_floor=coverage_floor,
    )


def test_abstain_on_empty():
    col = getEmptyCol()
    r = _topic_mastery(col)
    assert r.abstain is True
    assert len(r.topics) == 9
    assert len(r.abstain_reasons) >= 1


def test_thresholds_echoed():
    col = getEmptyCol()
    r = _topic_mastery(col, mastered_threshold=0.5, review_floor=5, coverage_floor=0.3)
    assert abs(r.thresholds.mastered_threshold - 0.5) < 1e-6
    assert r.thresholds.review_floor == 5
    assert abs(r.thresholds.coverage_floor - 0.3) < 1e-6


def test_tagged_without_fsrs_still_abstains():
    col = getEmptyCol()
    basic = col.models.by_name("Basic")
    assert basic is not None
    for key in SUBJECT_KEYS:
        deck_id = col.decks.id(f"PGRE::{key}")
        note_ids = []
        for i in range(3):
            note = col.new_note(basic)
            note["Front"] = f"[{key}] q{i + 1}"
            note["Back"] = f"a{i + 1}"
            col.add_note(note, deck_id)
            note_ids.append(note.id)
        col.tags.bulk_add(note_ids, f"pgre::{key}")

    r = _topic_mastery(col)
    # No card has an FSRS memory_state (nothing was reviewed under FSRS), so the
    # backend must refuse to score.
    assert r.abstain is True
    assert any(
        ("review" in reason.lower())
        or ("fsrs" in reason.lower())
        or ("coverage" in reason.lower())
        for reason in r.abstain_reasons
    )
    # Honesty metadata is populated even when abstaining.
    assert r.updated_at_millis > 0
    assert r.thresholds.review_floor == 20


def test_public_wrapper():
    # S4: the public `col.speedrun` wrapper avoids `_backend` (and needs no
    # manual `import anki.speedrun_pb2`).
    col = getEmptyCol()
    r = col.speedrun.topic_mastery()
    assert r.abstain is True
    assert len(r.topics) == 9
    assert r.thresholds.review_floor == 20  # default applied
    # overrides pass through
    r2 = col.speedrun.topic_mastery(mastered_threshold=0.5, review_floor=5)
    assert abs(r2.thresholds.mastered_threshold - 0.5) < 1e-6
    assert r2.thresholds.review_floor == 5


def test_deck_mastery_groups_by_deck():
    # Per-deck view (general, not PGRE-specific): one row per deck with cards.
    col = getEmptyCol()
    basic = col.models.by_name("Basic")
    assert basic is not None
    for deck in ("Alpha", "Beta"):
        did = col.decks.id(deck)
        for i in range(3):
            note = col.new_note(basic)
            note["Front"] = f"{deck} {i}"
            note["Back"] = str(i)
            col.add_note(note, did)
    r = col.speedrun.deck_mastery()
    by_name = {d.deck_name: d for d in r.decks}
    assert "Alpha" in by_name and "Beta" in by_name
    assert by_name["Alpha"].total_cards == 3
    # No FSRS memory state yet → nothing mastered.
    assert by_name["Alpha"].mastered == 0
    assert by_name["Alpha"].cards_with_state == 0


def test_honesty_shape():
    col = getEmptyCol()
    r = _topic_mastery(col)

    assert isinstance(r.abstain, bool)
    assert isinstance(list(r.abstain_reasons), list)
    assert isinstance(r.memory_score, float)
    assert isinstance(r.score_low, float)
    assert isinstance(r.score_high, float)
    assert isinstance(r.coverage, float)
    assert isinstance(r.total_reviews, int)
    assert isinstance(r.confidence, str)
    assert isinstance(list(r.reasons), list)
    assert isinstance(r.updated_at_millis, int)

    assert isinstance(r.thresholds.mastered_threshold, float)
    assert isinstance(r.thresholds.review_floor, int)
    assert isinstance(r.thresholds.coverage_floor, float)

    topics = list(r.topics)
    assert len(topics) == 9
    for topic in topics:
        assert topic.tag.startswith("pgre::")
        assert isinstance(topic.name, str)
        assert isinstance(topic.weight, float)
        assert isinstance(topic.total_cards, int)
        assert isinstance(topic.cards_with_state, int)
        assert isinstance(topic.mastered, int)
        assert isinstance(topic.mean_retrievability, float)
        assert isinstance(topic.mean_stability, float)
        assert isinstance(topic.median_latency_ms, int)
