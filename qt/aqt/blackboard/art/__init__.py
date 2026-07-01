# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Per-subject chalk drawings for the blackboard screens.

One module per PGRE taxonomy subject (module name == taxonomy key, see
``aqt.blackboard.SUBJECT_KEYS``). Each module is pure data and must define:

``SVG: str``
    A complete ``<svg>`` element drawn to look like chalk on slate. Contract:

    * root: ``<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg" aria-hidden="true">``
    * strokes only (``fill="none"`` except for small dots/hatching), colors
      from ``aqt.blackboard``: CHALK_WHITE ``#f0ead6``, CHALK_YELLOW
      ``#ffd9a0``, CHALK_BLUE ``#bfe3ff``, CHALK_PINK ``#ffc4c4``,
      CHALK_GREEN ``#c8f0c8``
    * chalk feel: ``stroke-linecap="round"``, slightly wobbly hand-drawn
      paths (avoid perfect straight primitives for long lines), group
      opacity 0.25–0.5 so it reads as background
    * the middle band (roughly x 220–780, y 60–420) is where the deck title,
      counts, and Study button sit — keep it sparse there; put the dense
      drawings toward the corners and edges
    * ``<text>`` labels are welcome (formulas, axis labels) using
      ``font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS',
      cursive"``; plain-text math only (no MathJax in the art layer)
    * self-contained: no scripts, no external refs, no images

``TAGLINE: str``
    A short (< 60 chars) chalk-written phrase shown under the deck title,
    e.g. a landmark formula for the subject. Plain text/unicode, no HTML.

Validated in ``qt/tests/test_blackboard.py`` (XML well-formedness + the
contract above), so a bad drawing fails CI rather than blanking the board.
"""
