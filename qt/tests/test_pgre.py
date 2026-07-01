# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the Physics GRE fork: bundled default decks + manifold home HTML.

These exercise the GUI-free logic in ``aqt.pgre`` against a real (temporary)
collection, so no running Qt app is needed. The bundled ``.apkg`` files are read
from the in-repo source data folder (``qt/aqt/data/decks``).
"""

from __future__ import annotations

import html
import os
import tempfile

from anki.collection import Collection
from aqt import pgre

DECK_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "aqt", "data", "decks")
)


def _empty_col() -> Collection:
    tmp = tempfile.mkdtemp()
    return Collection(os.path.join(tmp, "collection.anki2"))


def test_subjects_and_bundled_files_present():
    # Exactly the 9 PGRE subjects; 9 deck spikes + 1 "more decks" spike = 10.
    assert len(pgre.SUBJECTS) == 9
    assert pgre.MANIFOLD_POINTS == 10
    assert pgre.DECKS_PER_PAGE == 9
    assert len(pgre._point_positions()) == pgre.MANIFOLD_POINTS
    assert pgre.SUBJECTS[0].deck_name == "PGRE::Classical Mechanics"
    for subject in pgre.SUBJECTS:
        path = os.path.join(DECK_DIR, subject.apkg)
        assert os.path.exists(path), f"missing bundled deck: {subject.apkg}"


def test_import_default_decks_seeds_and_is_idempotent():
    col = _empty_col()
    imported = pgre.import_default_decks(col, DECK_DIR)

    # The 9 subject decks plus the bundled Speed Recall formula deck.
    assert len(imported) == 10
    for subject in pgre.SUBJECTS:
        assert col.decks.by_name(subject.deck_name) is not None
    assert pgre.SPEED_RECALL_DECK in imported
    assert col.decks.by_name(pgre.SPEED_RECALL_DECK) is not None
    assert col.get_config(pgre.DECKS_IMPORTED_KEY, False) is True

    # A second call must not duplicate anything.
    assert pgre.import_default_decks(col, DECK_DIR) == []


def test_maybe_import_respects_flag():
    col = _empty_col()
    col.set_config(pgre.DECKS_IMPORTED_KEY, True)
    assert pgre.maybe_import_default_decks(col) == []
    # Flag set, so nothing was imported.
    assert col.decks.by_name("PGRE::Classical Mechanics") is None


def test_manifold_html_links_each_imported_deck():
    col = _empty_col()
    pgre.import_default_decks(col, DECK_DIR)
    rendered = pgre.build_manifold_html(col)

    # The equation-drawn manifold SVG, classic-list link, and the "More decks"
    # spike are present. Exactly 9 decks fit on one page, so depth 0 shows them.
    assert 'id="cy-svg"' in rendered
    assert "<polygon" in rendered
    assert "pycmd('classic')" in rendered
    # Drag-to-rotate wiring: the spin script and per-button base coordinates it
    # orbits so buttons follow the manifold. No on-screen rotation controls.
    assert "<script>" in rendered
    assert "data-cx=" in rendered
    assert "cy-controls" not in rendered
    assert "More decks" in rendered
    assert "pycmd('more')" in rendered
    assert pgre.page_count(col) == 1

    # Every subject label shows (HTML-escaped), and each resolves to an
    # open:<deck_id> command.
    for subject in pgre.SUBJECTS:
        assert html.escape(subject.label) in rendered
        deck = col.decks.by_name(subject.deck_name)
        assert deck is not None
        assert f"pycmd('open:{deck['id']}')" in rendered


def test_manifold_html_empty_when_no_decks():
    col = _empty_col()  # nothing imported; only the empty Default deck exists
    rendered = pgre.build_manifold_html(col)

    # No decks to show: deck spikes are left empty (no open commands), but the
    # manifold SVG, the "More decks" spike, and the classic link still render.
    assert 'id="cy-svg"' in rendered
    assert "pycmd('open:" not in rendered
    assert "More decks" in rendered
    assert "pycmd('classic')" in rendered


def test_manifold_depth_pages_through_decks():
    col = _empty_col()
    pgre.import_default_decks(col, DECK_DIR)
    # Add extra decks so there are two pages (9 subjects + 3 = 12 decks).
    for name in ("Extra A", "Extra B", "Extra C"):
        col.decks.add_normal_deck_with_name(name)

    assert pgre.page_count(col) == 2
    entries = pgre._display_decks(col)
    assert len(entries) == 12
    # Subjects come first (curated order), extras follow.
    assert entries[0][1] == pgre.SUBJECTS[0].label

    # Depth 0 shows the first 9 decks; depth 1 shows the remaining 3.
    page0 = pgre.build_manifold_html(col, depth=0)
    page1 = pgre.build_manifold_html(col, depth=1)
    assert f"pycmd('open:{entries[0][0]}')" in page0
    assert f"pycmd('open:{entries[0][0]}')" not in page1
    assert f"pycmd('open:{entries[9][0]}')" in page1
    assert f"pycmd('open:{entries[9][0]}')" not in page0

    # Depth wraps modulo the page count, so depth 2 == depth 0.
    assert pgre.build_manifold_html(col, depth=2) == page0
