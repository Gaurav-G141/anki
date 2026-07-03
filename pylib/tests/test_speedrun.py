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


def _add_tagged_cards(col, key, n, deck_root="PGRE"):
    """Add `n` Basic notes tagged pgre::<key> in a subject deck; return card ids."""
    basic = col.models.by_name("Basic")
    assert basic is not None
    deck_id = col.decks.id(f"{deck_root}::{key}")
    cids = []
    note_ids = []
    for i in range(n):
        note = col.new_note(basic)
        note["Front"] = f"[{key}] q{i}"
        note["Back"] = f"a{i}"
        col.add_note(note, deck_id)
        note_ids.append(note.id)
        cids.append(note.card_ids()[0])
    col.tags.bulk_add(note_ids, f"pgre::{key}")
    return cids


def _review(col, cid, ease):
    card = col.get_card(cid)
    card.start_timer()
    col.sched.answerCard(card, ease)


def test_three_scores_shape():
    # Every score ships as its own sub-block with a range + confidence + abstain.
    col = getEmptyCol()
    r = _topic_mastery(col)
    for field in ("performance_abstain", "readiness_abstain"):
        assert isinstance(getattr(r, field), bool)
    assert isinstance(r.performance_score, float)
    assert isinstance(r.performance_low, float)
    assert isinstance(r.performance_high, float)
    assert isinstance(r.performance_confidence, str)
    assert isinstance(list(r.performance_reasons), list)
    assert isinstance(r.readiness_score, float)
    assert isinstance(r.readiness_low, float)
    assert isinstance(r.readiness_high, float)
    assert isinstance(r.readiness_confidence, str)
    # per-topic accuracy field
    assert all(isinstance(t.accuracy, float) for t in r.topics)


def test_performance_independent_of_memory_abstain():
    # Tag all subjects and review (default SM2 scheduler, so NO FSRS memory
    # state). Memory must abstain (no state) while Performance + Readiness score
    # from the grade history — per-score independent abstain.
    col = getEmptyCol()
    for key in SUBJECT_KEYS:
        for cid in _add_tagged_cards(col, key, 2):
            _review(col, cid, 3)  # Good
            _review(col, cid, 3)
    r = _topic_mastery(col)
    assert r.abstain is True, "memory should abstain without FSRS state"
    assert any("fsrs" in reason.lower() for reason in r.abstain_reasons)
    assert r.performance_abstain is False, "performance should score from grades"
    assert r.readiness_abstain is False
    assert r.performance_low <= r.performance_score <= r.performance_high
    assert 200.0 <= r.readiness_score <= 990.0
    assert r.readiness_low <= r.readiness_score <= r.readiness_high


def test_dummy_account_moderate_progress():
    """A 'dummy account' with moderate progress: FSRS on, all subjects covered,
    a realistic mix of grades. All three scores must be shown honestly — each
    with a range, none abstaining — and readiness must land on the 200–990
    scale in 10-point increments."""
    col = getEmptyCol()
    col.set_config("fsrs", True)
    for key in SUBJECT_KEYS:
        cids = _add_tagged_cards(col, key, 4)
        # 3 answered Good, 1 answered Again -> 75% accuracy, all get FSRS state.
        for cid in cids[:3]:
            _review(col, cid, 3)
        _review(col, cids[3], 1)

    r = _topic_mastery(col)

    # Memory: real, ranged, not abstaining.
    assert r.abstain is False, f"memory abstained: {list(r.abstain_reasons)}"
    assert 0.0 <= r.memory_score <= 1.0
    assert r.score_low <= r.memory_score <= r.score_high
    assert r.confidence
    # some card actually carries FSRS state
    assert sum(t.cards_with_state for t in r.topics) > 0

    # Performance: real, ranged.
    assert r.performance_abstain is False, list(r.performance_abstain_reasons)
    assert 0.0 <= r.performance_score <= 1.0
    assert r.performance_low <= r.performance_score <= r.performance_high
    assert r.performance_confidence

    # Readiness: projected onto the ETS scale, ranged, 10-pt increments.
    assert r.readiness_abstain is False, list(r.readiness_abstain_reasons)
    assert 200.0 <= r.readiness_score <= 990.0
    assert r.readiness_low <= r.readiness_score <= r.readiness_high
    assert r.readiness_low >= 200.0 and r.readiness_high <= 990.0
    assert r.readiness_score % 10 == 0
    assert r.readiness_confidence and r.readiness_confidence != "high"

    # Full coverage since every subject has cards.
    assert r.coverage > 0.99


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
