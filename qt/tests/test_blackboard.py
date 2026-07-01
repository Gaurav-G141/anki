# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the blackboard subject screens (aqt.blackboard).

GUI-free: exercises the deck-name → subject mapping, the nine chalk-art
modules' contract (see ``aqt/blackboard/art/__init__.py``), and the assembled
board HTML.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from aqt import blackboard
from aqt.pgre import SUBJECTS

ALL_KEYS = list(blackboard.SUBJECT_KEYS.values())

CHALK_COLORS = {
    blackboard.CHALK_WHITE,
    blackboard.CHALK_YELLOW,
    blackboard.CHALK_BLUE,
    blackboard.CHALK_PINK,
    blackboard.CHALK_GREEN,
}


def test_every_subject_has_a_key():
    # The mapping mirrors the 9 bundled subjects exactly.
    assert len(blackboard.SUBJECT_KEYS) == 9
    assert {s.name for s in SUBJECTS} == set(blackboard.SUBJECT_KEYS)
    assert len(set(ALL_KEYS)) == 9


def test_subject_key_for_deck():
    assert (
        blackboard.subject_key_for_deck("PGRE::Electromagnetism") == "electromagnetism"
    )
    # Subdecks and the Speed Recall tree resolve too.
    assert (
        blackboard.subject_key_for_deck("PGRE::Quantum Mechanics::Extra")
        == "quantum_mechanics"
    )
    assert (
        blackboard.subject_key_for_deck("Speed Recall::Optics & Waves")
        == "optics_waves"
    )
    # Non-subject decks don't get a board.
    assert blackboard.subject_key_for_deck("Default") is None
    assert blackboard.subject_key_for_deck("PGRE") is None


@pytest.mark.parametrize("key", ALL_KEYS)
def test_art_module_contract(key: str):
    art = blackboard.board_art(key)
    assert art.key == key

    # Tagline: short plain text, no markup.
    assert art.tagline.strip()
    assert len(art.tagline) < 60
    assert "<" not in art.tagline

    # SVG: well-formed XML with the required root attributes.
    root = ET.fromstring(art.svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("viewBox") == "0 0 1000 560"
    assert root.get("aria-hidden") == "true"
    assert root.get("preserveAspectRatio") == "xMidYMid slice"

    # Self-contained: no scripts or external references.
    svg_lower = art.svg.lower()
    assert "<script" not in svg_lower
    assert "http://" not in svg_lower.replace("http://www.w3.org/", "")
    assert "xlink:href" not in art.svg

    # It actually draws something, in chalk colors only.
    assert (
        art.svg.count("<path")
        + art.svg.count("<circle")
        + art.svg.count("<ellipse")
        + art.svg.count("<rect")
        + art.svg.count("<line")
        + art.svg.count("<polyline")
        >= 5
    )
    used = {
        value
        for el in root.iter()
        for attr in ("stroke", "fill")
        if (value := el.get(attr)) not in (None, "none")
    }
    assert used, "art must set stroke/fill colors"
    assert used <= CHALK_COLORS, f"non-chalk colors used: {used - CHALK_COLORS}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_board_html_assembles(key: str):
    rendered = blackboard.blackboard_page_html(
        key,
        f"PGRE::{key}",
        "",
        "<p>",
        "<table><tr><td>New:</td></tr></table>",
    )
    assert 'id="bb-board"' in rendered
    assert 'id="bb-art"' in rendered
    assert "<svg" in rendered
    # Title is the last deck path component.
    assert f'<h1 id="bb-title">{key}</h1>' in rendered
