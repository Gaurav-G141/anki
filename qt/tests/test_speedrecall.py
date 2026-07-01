# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for Speed Recall's latency-modulated scheduling + interleaved queue.

Pure-logic tests need no collection; the queue/store tests use a temporary
``Collection`` with a few ``PGRE::<subject>`` decks. No running Qt app needed.
"""

from __future__ import annotations

import os
import random
import tempfile

import pytest

from anki.collection import Collection
from aqt import speedrecall as sr


def _empty_col() -> Collection:
    tmp = tempfile.mkdtemp()
    return Collection(os.path.join(tmp, "collection.anki2"))


def _add_cards(col: Collection, deck_name: str, n: int) -> list[int]:
    did = col.decks.id(deck_name)
    nt = col.models.by_name("Basic")
    cids = []
    for i in range(n):
        note = col.new_note(nt)
        note["Front"] = f"{deck_name} front {i}"
        note["Back"] = f"back {i}"
        col.add_note(note, did)
        cids.extend(col.card_ids_of_note(note.id))
    return cids


# --- latency curve --------------------------------------------------------


def test_latency_factor_bounds_and_monotonic():
    assert sr.latency_factor(0) == 1.0
    assert sr.latency_factor(sr.FAST_SECONDS) == 1.0
    assert sr.latency_factor(sr.SLOW_SECONDS) == sr.SLOW_FLOOR
    assert sr.latency_factor(120) == sr.SLOW_FLOOR
    # strictly non-increasing across the ramp
    prev = 1.0
    for t in range(0, 70, 2):
        f = sr.latency_factor(t)
        assert f <= prev + 1e-9
        assert sr.SLOW_FLOOR - 1e-9 <= f <= 1.0 + 1e-9
        prev = f


def test_easy_matches_product_spec():
    # Fast Easy ≈ 1 week; slow (>1 min) Easy ≈ 12 hours.
    assert sr.next_interval_hours(4, 3.0) == pytest.approx(168.0)  # a few seconds
    slow_easy = sr.next_interval_hours(4, 75.0)
    assert slow_easy == pytest.approx(168.0 * sr.SLOW_FLOOR)
    assert 11.0 <= slow_easy <= 13.0  # ~12h


def test_again_is_short_and_latency_independent():
    assert sr.next_interval_hours(1, 2.0) == sr.next_interval_hours(1, 90.0)
    assert sr.next_interval_hours(1, 2.0) < 1.0  # under an hour


def test_slower_recall_never_increases_interval():
    for rating in (2, 3, 4):
        fast = sr.next_interval_hours(rating, 3.0)
        slow = sr.next_interval_hours(rating, 90.0)
        assert slow < fast


def test_invalid_rating():
    with pytest.raises(ValueError):
        sr.next_interval_hours(5, 1.0)


def test_format_interval():
    assert sr.format_interval(1 / 6) == "10m"
    assert sr.format_interval(12) == "12h"
    assert sr.format_interval(168) == "7d"


# --- schedule store -------------------------------------------------------


def test_record_and_due():
    col = _empty_col()
    cids = _add_cards(col, "PGRE::Classical Mechanics", 1)
    cid = cids[0]
    # Easy + fast → ~7d out → not due now.
    sr.record_answer(col, cid, 4, 3.0, now=1000.0)
    assert cid not in sr.due_card_ids(col, now=1000.0)
    # …but due once its interval has elapsed.
    assert cid in sr.due_card_ids(col, now=1000.0 + 8 * 86400)


# --- interleaved queue ----------------------------------------------------


def test_build_queue_interleaves_subjects():
    col = _empty_col()
    _add_cards(col, "PGRE::Classical Mechanics", 5)
    _add_cards(col, "PGRE::Electromagnetism", 5)
    _add_cards(col, "PGRE::Quantum Mechanics", 5)
    rng = random.Random(0)
    q = sr.build_queue(col, limit=9, now=1000.0, rng=rng)
    assert len(q) == 9
    subjects = [col.decks.name(col.get_card(c).did) for c in q]
    # First three cards should span three different subjects (round-robin).
    assert len(set(subjects[:3])) == 3


def test_build_queue_nonempty_when_nothing_due():
    col = _empty_col()
    _add_cards(col, "PGRE::Optics & Waves", 3)
    # Schedule all of them far in the future → nothing "due"…
    for c in col.find_cards('deck:"PGRE::Optics & Waves"'):
        sr.record_answer(col, c, 4, 1.0, now=1000.0)
    # …but a session still offers free practice rather than being empty.
    q = sr.build_queue(col, limit=10, now=1000.0)
    assert len(q) == 3
