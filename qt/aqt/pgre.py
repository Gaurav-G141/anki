# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Physics GRE fork: bundled default decks + the Calabi-Yau home screen model.

This module holds the fork-specific, GUI-free logic:

* the 9 PGRE subject decks that ship with the app (the "categorized decks"),
* first-run auto-import of those decks into a fresh collection, and
* the HTML for the Calabi-Yau manifold home screen (each of the manifold's
  outer points is a button into one subject deck).

Keeping this here (rather than inside ``main.py``/``manifold.py``) lets the
import + HTML logic be unit-tested against a bare ``Collection`` without a
running Qt app (see ``qt/tests/test_pgre.py``).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from anki.collection import Collection

#: Collection config flag: True once the bundled decks have been seeded, so we
#: never re-import (and never fight a user who deletes a seeded deck).
DECKS_IMPORTED_KEY = "pgreDefaultDecksImported"

#: Parent deck the bundled subject decks live under (``PGRE::<Subject>``).
PGRE_PARENT = "PGRE"


@dataclass(frozen=True)
class Subject:
    """One PGRE subject: its deck name, bundled file, and short button label."""

    name: str  # deck subname, e.g. "Classical Mechanics" -> PGRE::Classical Mechanics
    apkg: str  # bundled filename under the data/decks folder
    label: str  # text shown on the manifold button

    @property
    def deck_name(self) -> str:
        return f"{PGRE_PARENT}::{self.name}"


#: The 9 subjects, in the order they sit around the manifold (point 1 = top,
#: going clockwise). Mirrors ``speedrun/taxonomy.py`` and the numbered files in
#: the repo's ``categorized decks/`` folder. The 10th manifold point is always
#: an "add more decks" entry (see ``build_manifold_html``).
SUBJECTS: list[Subject] = [
    Subject(
        "Classical Mechanics", "01_Classical_Mechanics.apkg", "Classical Mechanics"
    ),
    Subject("Electromagnetism", "02_Electromagnetism.apkg", "Electromagnetism"),
    Subject("Quantum Mechanics", "03_Quantum_Mechanics.apkg", "Quantum Mechanics"),
    Subject("Atomic Physics", "04_Atomic_Physics.apkg", "Atomic Physics"),
    Subject(
        "Thermodynamics & Statistical Mechanics",
        "05_Thermodynamics_Statistical_Mechanics.apkg",
        "Thermodynamics & Stat Mech",
    ),
    Subject("Optics & Waves", "06_Optics_Waves.apkg", "Optics & Waves"),
    Subject("Specialized Topics", "07_Specialized_Topics.apkg", "Specialized Topics"),
    Subject("Special Relativity", "08_Special_Relativity.apkg", "Special Relativity"),
    Subject("Laboratory Methods", "09_Laboratory_Methods.apkg", "Laboratory Methods"),
]

#: Total outer points (spikes) on the manifold. The first 9 map to subjects; the
#: last one is always the "add more decks" spike.
MANIFOLD_POINTS = 10


# Bundled decks + first-run import
######################################################################


def default_deck_dir() -> str:
    """Filesystem folder holding the bundled ``.apkg`` files at runtime."""
    from aqt.utils import aqt_data_path

    return str(aqt_data_path() / "decks")


def import_default_decks(col: Collection, deck_dir: str | None = None) -> list[str]:
    """Import any bundled subject decks not already present.

    Idempotent: a subject whose ``PGRE::<name>`` deck already exists is skipped,
    and the ``DECKS_IMPORTED_KEY`` flag is set so callers can short-circuit on
    later runs. Returns the deck names that were imported this call.
    """
    from anki.collection import ImportAnkiPackageRequest

    if deck_dir is None:
        deck_dir = default_deck_dir()

    imported: list[str] = []
    for subject in SUBJECTS:
        if col.decks.by_name(subject.deck_name) is not None:
            continue
        path = os.path.join(deck_dir, subject.apkg)
        if not os.path.exists(path):
            continue
        col.import_anki_package(ImportAnkiPackageRequest(package_path=path))
        imported.append(subject.deck_name)

    col.set_config(DECKS_IMPORTED_KEY, True)
    return imported


def maybe_import_default_decks(col: Collection) -> list[str]:
    """Seed the bundled decks once per collection. No-op after the first run."""
    if col.get_config(DECKS_IMPORTED_KEY, False):
        return []
    return import_default_decks(col)


# Calabi-Yau manifold home screen
######################################################################
#
# The manifold is the transparent Calabi-Yau PNG (served from the imgs folder).
# A point-button sits on each of its outer spikes. The image's spikes are not
# evenly spaced (it's a 3D projection), so the button positions below are hand-
# placed on the actual spike tips rather than computed from a circle.
#
# Decks are shown 9-per-page and paged through by "depth": depth 0 is the first
# 9 decks, depth 1 the next 9, and so on. The 10th spike is a "More decks"
# button that advances to the next depth (see ``Manifold`` in ``manifold.py``).

CALABI_YAU_IMG = "/_anki/imgs/calabi-yau.png"

#: Decks shown per manifold page (the 9 deck spikes; the 10th is "More decks").
DECKS_PER_PAGE = 9

#: (left%, top%) of each spike tip in ``calabi-yau.png``, as a percentage of the
#: (square) stage. Clockwise from the top; indices 0..8 hold decks and index 9 is
#: the "More decks" spike. Detected from the image's silhouette (the farthest
#: opaque pixel per angle) — regenerate these if the artwork is replaced.
_SPIKE_POSITIONS: list[tuple[float, float]] = [
    (51.6, 10.8),  # top
    (75.5, 20.7),  # upper-right
    (86.2, 38.8),  # right
    (84.0, 65.7),  # lower-right
    (70.5, 81.4),  # bottom-right
    (42.8, 87.6),  # bottom
    (25.3, 79.5),  # bottom-left
    (11.9, 55.3),  # left
    (13.5, 34.3),  # upper-left
    (29.8, 16.3),  # top-left (More decks)
]

#: How far to pull each button in from its spike tip toward the centre (1.0 =
#: sit exactly on the tip). A slight pull keeps the tip poking out past the label.
_INWARD = 0.97


def _point_positions() -> list[tuple[float, float]]:
    """(left%, top%) for each of the ``MANIFOLD_POINTS`` spike buttons."""
    return [
        (50.0 + (left - 50.0) * _INWARD, 50.0 + (top - 50.0) * _INWARD)
        for left, top in _SPIKE_POSITIONS
    ]


def _display_decks(col: Collection) -> list[tuple[int, str]]:
    """Ordered ``(deck_id, label)`` for every deck shown across the manifold.

    Curated PGRE subjects come first (nice labels, in taxonomy order); any other
    real decks follow, alphabetically. The empty Default deck, the ``PGRE``
    parent container, and filtered decks are omitted. This is the full list that
    ``build_manifold_html`` pages through by depth.
    """
    entries: list[tuple[int, str]] = []
    seen: set[int] = set()
    for subject in SUBJECTS:
        deck = col.decks.by_name(subject.deck_name)
        if deck is not None:
            did = int(deck["id"])
            entries.append((did, subject.label))
            seen.add(did)
    for item in col.decks.all_names_and_ids(
        skip_empty_default=True, include_filtered=False
    ):
        did = int(item.id)
        if did in seen or item.name == PGRE_PARENT:
            continue
        entries.append((did, item.name.split("::")[-1]))
    return entries


def page_count(col: Collection) -> int:
    """Number of manifold depths needed to show every deck (at least 1)."""
    decks = len(_display_decks(col))
    return max(1, math.ceil(decks / DECKS_PER_PAGE))


def build_manifold_html(col: Collection, depth: int = 0) -> str:
    """Return the home-screen HTML: the manifold image + 10 spike-buttons.

    ``depth`` selects which 9 decks are shown: depth ``n`` shows decks
    ``n*9 .. n*9+8`` on the deck spikes (indices 0..8). It wraps modulo the
    number of pages, so an out-of-range depth is always valid. Any deck spike
    with no deck for this page is left empty. The 10th spike (index 9) is always
    a "More decks" button (``pycmd('more')``) that advances to the next depth.
    """
    import html

    entries = _display_decks(col)
    pages = max(1, math.ceil(len(entries) / DECKS_PER_PAGE))
    depth %= pages
    start = depth * DECKS_PER_PAGE
    page = entries[start : start + DECKS_PER_PAGE]

    positions = _point_positions()
    buttons: list[str] = []
    for index, (left, top) in enumerate(positions):
        style = f"left:{left:.2f}%;top:{top:.2f}%"
        if index >= DECKS_PER_PAGE:
            # The final spike advances to the next page of decks.
            buttons.append(
                f"<button class='cy-point cy-more' style='{style}' "
                f"title='Show more decks' onclick=\"pycmd('more')\">"
                f"<span class='cy-num'>&raquo;</span>More decks</button>"
            )
            continue
        if index >= len(page):
            # No deck for this slot at this depth — leave the spike empty.
            continue
        did, raw_label = page[index]
        label = html.escape(raw_label)
        buttons.append(
            f"<button class='cy-point' style='{style}' "
            f"onclick=\"pycmd('open:{did}')\">"
            f"<span class='cy-num'>{start + index + 1}</span>{label}</button>"
        )

    if pages > 1:
        page_info = (
            f"Depth {depth} — decks {start + 1}–{start + len(page)} of {len(entries)}"
        )
    else:
        page_info = ""

    return _MANIFOLD_BODY.format(
        img=CALABI_YAU_IMG,
        buttons="\n".join(buttons),
        page_info=html.escape(page_info),
    )


#: Inline styles + markup for the manifold screen. Kept self-contained so no
#: extra build rule (scss compile) is needed for the home screen.
_MANIFOLD_BODY = """
<style>
  #cy-wrap {{ text-align: center; }}
  #cy-title {{ font-size: 26px; font-weight: 700; margin: 12px 0 2px; }}
  #cy-sub {{ font-size: 13px; opacity: 0.7; margin-bottom: 2px; }}
  #cy-page {{ font-size: 12px; opacity: 0.55; margin-bottom: 6px; min-height: 1em; }}
  #cy-stage {{
    position: relative;
    width: min(84vmin, 820px);
    aspect-ratio: 1 / 1;
    margin: 0 auto;
    overflow: visible;
  }}
  #cy-stage > img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    position: absolute;
    inset: 0;
    user-select: none;
    -webkit-user-drag: none;
    pointer-events: none;
  }}
  .cy-point {{
    position: absolute;
    transform: translate(-50%, -50%);
    max-width: 132px;
    padding: 6px 11px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    background: rgba(20, 20, 28, 0.82);
    color: #fff;
    font: inherit;
    font-size: 12.5px;
    line-height: 1.15;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    transition: transform 0.08s ease, background 0.08s ease;
  }}
  .cy-point:hover {{
    background: rgba(46, 108, 224, 0.95);
    transform: translate(-50%, -50%) scale(1.06);
  }}
  .cy-num {{
    display: inline-block;
    min-width: 1.2em;
    margin-right: 5px;
    font-weight: 700;
    opacity: 0.75;
  }}
  .cy-more {{
    background: rgba(46, 108, 224, 0.6);
    border-style: dashed;
    border-color: rgba(160, 195, 255, 0.8);
  }}
  .cy-more:hover {{ background: rgba(46, 108, 224, 0.95); }}
  #cy-classic {{ margin-top: 14px; }}
  #cy-classic a {{ cursor: pointer; text-decoration: underline; opacity: 0.85; }}
</style>
<div id="cy-wrap">
  <div id="cy-title">Ankimatter</div>
  <div id="cy-sub">the best app to prepare for the Physics GRE</div>
  <div id="cy-page">{page_info}</div>
  <div id="cy-stage">
    <img src="{img}" alt="Calabi-Yau manifold">
    {buttons}
  </div>
  <div id="cy-classic">
    <a onclick="pycmd('classic')">Classic deck list</a>
  </div>
</div>
"""
