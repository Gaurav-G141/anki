# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Blackboard-themed subject screens (Physics GRE fork).

When the user opens one of the 9 bundled ``PGRE::<subject>`` decks from the
manifold, the deck overview is drawn as a chalkboard: a dark board in a wooden
frame, the deck name hand-written in chalk, the study counts as a chalk tally,
and — the point of the whole thing — a full-board chalk drawing themed to the
subject (circuits for Electromagnetism, potential wells for Quantum Mechanics,
a Carnot cycle for Thermo, ...).

The per-subject drawings live in ``aqt.blackboard.art.<key>`` (one module per
taxonomy subject, keys mirroring ``speedrun/taxonomy.py``). Each module is pure
data: a ``SVG`` string (the board-sized drawing) and a ``TAGLINE`` (a short
chalk-written phrase under the title). This module supplies the shared frame
and is unit-tested GUI-free in ``qt/tests/test_blackboard.py``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

from aqt.pgre import SUBJECTS

#: Taxonomy key (== art module name) for each bundled subject deck name.
#: Mirrors ``speedrun/taxonomy.py``; keep the two in sync.
SUBJECT_KEYS: dict[str, str] = {
    "Classical Mechanics": "classical_mechanics",
    "Electromagnetism": "electromagnetism",
    "Quantum Mechanics": "quantum_mechanics",
    "Atomic Physics": "atomic_physics",
    "Thermodynamics & Statistical Mechanics": "thermo_stat_mech",
    "Optics & Waves": "optics_waves",
    "Specialized Topics": "specialized_topics",
    "Special Relativity": "special_relativity",
    "Laboratory Methods": "lab_methods",
}

#: Chalk stroke palette shared by the art modules (documented here so the nine
#: drawings stay visually consistent).
CHALK_WHITE = "#f0ead6"
CHALK_YELLOW = "#ffd9a0"
CHALK_BLUE = "#bfe3ff"
CHALK_PINK = "#ffc4c4"
CHALK_GREEN = "#c8f0c8"


@dataclass(frozen=True)
class BoardArt:
    """One subject's chalk drawing + tagline."""

    key: str
    svg: str
    tagline: str


def subject_key_for_deck(deck_name: str) -> str | None:
    """Taxonomy key for a deck that belongs to a PGRE subject, else ``None``.

    Matches by path component so both ``PGRE::Electromagnetism`` (and its
    subdecks) and ``Speed Recall::Electromagnetism`` get the themed board.
    """
    components = deck_name.replace("\x1f", "::").split("::")
    for subject in SUBJECTS:
        if subject.name in components:
            return SUBJECT_KEYS[subject.name]
    return None


def board_art(key: str) -> BoardArt:
    """Load a subject's art module (``aqt.blackboard.art.<key>``)."""
    module = importlib.import_module(f"aqt.blackboard.art.{key}")
    return BoardArt(key=key, svg=module.SVG, tagline=module.TAGLINE)


def blackboard_page_html(
    key: str,
    deck_label: str,
    share_link: str,
    desc: str,
    table: str,
) -> str:
    """The full overview body for a subject deck, chalkboard-styled.

    ``deck_label`` must already be HTML-escaped; ``share_link``/``desc``/
    ``table`` are the same HTML fragments the stock overview renders, restyled
    by the chalk CSS so the study button and counts keep their behaviour.
    """
    art = board_art(key)
    title = deck_label.split("::")[-1].strip()
    return _BOARD_BODY.format(
        svg=art.svg,
        title=title,
        tagline=art.tagline,
        share_link=share_link,
        desc=desc,
        table=table,
    )


#: Chalk text font stack: real chalk/hand fonts where available, cursive
#: fallback. Also referenced by the art modules for their <text> labels.
CHALK_FONT = "'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive"

_BOARD_BODY = (
    """
<style>
  html, body {{ background: #2b2118; }}
  #bb-room {{
    max-width: 1060px;
    margin: 18px auto;
    padding: 18px;
    /* Wooden frame around the slate. */
    border-radius: 10px;
    background:
      repeating-linear-gradient(
        95deg,
        #6b4a2f 0px, #7a563a 22px, #6b4a2f 46px, #5d3f27 70px
      );
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.55), inset 0 0 6px rgba(0,0,0,0.6);
  }}
  #bb-board {{
    position: relative;
    overflow: hidden;
    /* Match the art's 1000x560 viewBox so the chalk drawing is never cropped. */
    aspect-ratio: 1000 / 560;
    min-height: 480px;
    border-radius: 4px;
    border: 2px solid rgba(0, 0, 0, 0.45);
    /* Slate: deep green with faint wipe marks. */
    background:
      radial-gradient(120% 90% at 30% 20%, rgba(255,255,255,0.045), transparent 60%),
      radial-gradient(100% 80% at 75% 75%, rgba(255,255,255,0.035), transparent 55%),
      linear-gradient(160deg, #29453a 0%, #223c33 45%, #1d352d 100%);
    color: {chalk_white};
    font-family: {chalk_font};
  }}
  #bb-art {{
    position: absolute;
    inset: 0;
    pointer-events: none;
  }}
  #bb-art svg {{ width: 100%; height: 100%; display: block; }}
  #bb-content {{
    position: relative;
    z-index: 1;
    text-align: center;
    padding: 34px 24px 30px;
  }}
  #bb-title {{
    font-size: 40px;
    letter-spacing: 0.02em;
    color: {chalk_white};
    text-shadow: 0 0 6px rgba(240, 234, 214, 0.35);
    margin: 0 0 4px;
  }}
  #bb-title::after {{
    /* Hand-drawn chalk underline. */
    content: "";
    display: block;
    width: 240px;
    margin: 6px auto 0;
    border-bottom: 3px solid rgba(240, 234, 214, 0.75);
    border-radius: 100% 40% / 8px 5px;
    transform: rotate(-0.6deg);
  }}
  #bb-tagline {{
    font-size: 17px;
    color: {chalk_yellow};
    opacity: 0.9;
    margin: 10px 0 6px;
  }}
  #bb-content .descfont {{
    color: {chalk_white};
    opacity: 0.85;
    max-width: 560px;
    margin: 6px auto;
  }}
  #bb-content .smallLink {{ color: {chalk_blue}; }}
  /* Restyle the stock counts table as a chalk tally. */
  #bb-content table {{ margin: 14px auto 0; }}
  #bb-content td {{
    font-size: 19px;
    color: {chalk_white};
    padding: 3px 8px;
  }}
  #bb-content .new-count {{ color: {chalk_blue}; }}
  #bb-content .learn-count {{ color: {chalk_pink}; }}
  #bb-content .review-count {{ color: {chalk_green}; }}
  #bb-content .bury-count {{ color: {chalk_yellow}; opacity: 0.8; }}
  /* The Study Now button: a chalk-outlined pill, "wiped brighter" on hover. */
  #bb-content button {{
    font-family: {chalk_font};
    font-size: 19px;
    color: {chalk_white};
    background: rgba(240, 234, 214, 0.07);
    border: 2.5px solid rgba(240, 234, 214, 0.85);
    border-radius: 255px 18px 225px 18px / 18px 225px 18px 255px;
    padding: 10px 30px;
    cursor: pointer;
    text-shadow: 0 0 5px rgba(240, 234, 214, 0.4);
    transition: background 0.1s ease, transform 0.1s ease;
  }}
  #bb-content button:hover {{
    background: rgba(240, 234, 214, 0.18);
    transform: rotate(-0.8deg) scale(1.04);
  }}
  /* Chalk rail + dust along the bottom of the frame. */
  #bb-rail {{
    height: 14px;
    margin: 10px 30px 0;
    border-radius: 3px;
    background: linear-gradient(#8a6543, #5d3f27);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
    position: relative;
  }}
  #bb-rail::before, #bb-rail::after {{
    content: "";
    position: absolute;
    top: -6px;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(#fffbe8, #cfc8ae);
    box-shadow: 0 1px 2px rgba(0,0,0,0.4);
  }}
  #bb-rail::before {{ left: 12%; width: 52px; }}
  #bb-rail::after {{
    right: 18%;
    width: 40px;
    background: linear-gradient(#ffe2b8, #d8b184);
  }}
</style>
<div id="bb-room">
  <div id="bb-board">
    <div id="bb-art">{svg}</div>
    <div id="bb-content">
      <h1 id="bb-title">{title}</h1>
      <div id="bb-tagline">{tagline}</div>
      {share_link}
      {desc}
      {table}
    </div>
  </div>
  <div id="bb-rail"></div>
</div>
""".replace("{chalk_font}", CHALK_FONT)
    .replace("{chalk_white}", CHALK_WHITE)
    .replace("{chalk_yellow}", CHALK_YELLOW)
    .replace("{chalk_blue}", CHALK_BLUE)
    .replace("{chalk_pink}", CHALK_PINK)
    .replace("{chalk_green}", CHALK_GREEN)
)
