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

import cmath
import colorsys
import functools
import math
import os
from collections.abc import Callable
from dataclasses import dataclass

from anki.collection import Collection
from anki.decks import DeckId

#: A 3D point and a meshed quad (its four corners), used by the Calabi-Yau
#: renderer below.
_Vec3 = tuple[float, float, float]
_Quad = list[_Vec3]
#: A depth-keyed, projected, shaded face: ``(depth, 2D polygon, "#rrggbb")``.
_Face = tuple[float, list[tuple[float, float]], str]
#: A render-ready face: ``(2D polygon, Lambert intensity, nearest-spike index)``.
#: The base colour is *not* stored here — it's derived from each spike's mastery
#: (red → green) at build time and multiplied by the intensity, so recolouring
#: never rebuilds the geometry.
_ShadedFace = tuple[tuple[tuple[float, float], ...], float, int]

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

#: Bundled Speed Recall formula deck (built from the Conquering the Physics GRE
#: equation index): filename under the data/decks folder + its top-level deck name.
SPEED_RECALL_APKG = "Speed_Recall_Formulas.apkg"
SPEED_RECALL_DECK = "Speed Recall"

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

    # The dedicated Speed Recall formula deck (Conquering the Physics GRE
    # equation index). Shipped with the app so every user gets it regardless of
    # account/progress; imported once, skipped if already present.
    sr_path = os.path.join(deck_dir, SPEED_RECALL_APKG)
    if col.decks.by_name(SPEED_RECALL_DECK) is None and os.path.exists(sr_path):
        col.import_anki_package(ImportAnkiPackageRequest(package_path=sr_path))
        imported.append(SPEED_RECALL_DECK)

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
# The manifold is drawn from its actual equations, not a picture. We mesh the
# standard cross-section of the Fermat quintic Calabi-Yau ``z1^n + z2^n = 1``
# (Hanson's parametrization): for each of the n*n branch patches (k1, k2),
#
#     z1 = e^{2πi·k1/n} · (cos w)^{2/n},   z2 = e^{2πi·k2/n} · (sin w)^{2/n}
#
# over the complex parameter ``w = a + i·b`` with ``a ∈ [0, π/2]``,
# ``b ∈ [-π/2, π/2]``. The 4D surface is projected to 3D via
# ``(Re z1, Re z2, Im z1·cosα + Im z2·sinα)``, rotated to a fixed view, and
# orthographically flattened to the 2D stage. Faces are depth-sorted (painter's
# algorithm) and Lambert-shaded, then emitted as inline SVG polygons.
#
# ``n = 5`` yields ten outer spikes; the button positions are the spike tips
# *detected from the projected geometry itself*, so a button always lands on a
# spike. The whole thing is collection-independent, so it's computed once and
# cached (``_manifold_geometry``).
#
# Decks are shown 9-per-page and paged through by "depth": depth 0 is the first
# 9 decks, depth 1 the next 9, and so on. The 10th spike is a "More decks"
# button that advances to the next depth (see ``Manifold`` in ``manifold.py``).

#: Decks shown per manifold page (the 9 deck spikes; the 10th is "More decks").
DECKS_PER_PAGE = 9

#: Calabi-Yau render parameters.
_CY_DEGREE = 5  # n: the quintic; gives MANIFOLD_POINTS (=10) outer spikes
_CY_RES = 16  # grid subdivisions per patch, per axis (higher = smoother)
_CY_ALPHA = math.pi / 4  # imaginary-part projection mix angle
_CY_ROT = (-1.05, 0.6)  # fixed view rotation (about x, then y), radians
_CY_PAD = 0.09  # fraction of the stage left as margin around the figure
#: Direction light arrives from, in the rotated view (x right, y up, z toward us).
_CY_LIGHT = (-0.35, -0.45, 0.82)

#: How far to pull each button in from its spike tip toward the centre (1.0 =
#: sit exactly on the tip). A slight pull keeps the tip poking out past the label.
_INWARD = 0.97

#: Subject mastery colour: a spike is red while its subject is unmastered and
#: shifts toward green as it is mastered. The three core subjects (Classical
#: Mechanics, Electromagnetism, Quantum Mechanics) use a concave mastery curve
#: (``m ** _CORE_MASTERY_EXP``), so they stay red for longer — only greening near
#: full mastery.
_HUE_RED = 0.0  # HSV hue for a fully-unmastered subject (red)
_HUE_GREEN = 0.33  # HSV hue for a fully-mastered subject (green)
_MASTERY_SAT = 0.70  # colour saturation (matches the old palette's vividness)
_MASTERY_VAL = 1.0  # base colour value before Lambert shading
_CORE_MASTERY_EXP = 2.5  # >1: core subjects need more mastery to turn green
_MATURE_IVL_DAYS = 21  # a card counts as "mastered" once its interval hits this


def _cy_rotate(p: _Vec3) -> _Vec3:
    """Rotate a 3D point into the fixed viewing orientation."""
    x, y, z = p
    rx, ry = _CY_ROT
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    y, z = y * cx - z * sx, y * sx + z * cx
    x, z = x * cy + z * sy, -x * sy + z * cy
    return (x, y, z)


def _cy_surface(k1: int, k2: int, a: float, b: float) -> _Vec3:
    """A point on the (k1, k2) branch of the Calabi-Yau cross-section."""
    n = _CY_DEGREE
    w = complex(a, b)
    z1 = cmath.exp(2j * math.pi * k1 / n) * (cmath.cos(w)) ** (2.0 / n)
    z2 = cmath.exp(2j * math.pi * k2 / n) * (cmath.sin(w)) ** (2.0 / n)
    z = z1.imag * math.cos(_CY_ALPHA) + z2.imag * math.sin(_CY_ALPHA)
    return _cy_rotate((z1.real, z2.real, z))


def _cy_quads() -> list[_Quad]:
    """Mesh every branch patch into quads of four rotated 3D corners."""
    n, res = _CY_DEGREE, _CY_RES
    quads: list[_Quad] = []
    for k1 in range(n):
        for k2 in range(n):
            for i in range(res):
                a0 = i / res * (math.pi / 2)
                a1 = (i + 1) / res * (math.pi / 2)
                for j in range(res):
                    b0 = -math.pi / 2 + j / res * math.pi
                    b1 = -math.pi / 2 + (j + 1) / res * math.pi
                    quads.append(
                        [
                            _cy_surface(k1, k2, a0, b0),
                            _cy_surface(k1, k2, a1, b0),
                            _cy_surface(k1, k2, a1, b1),
                            _cy_surface(k1, k2, a0, b1),
                        ]
                    )
    return quads


def _cy_projector(quads: list[_Quad]) -> Callable[[_Vec3], tuple[float, float]]:
    """Return a fn mapping a rotated 3D point to (x%, y%) filling the stage."""
    xs = [p[0] for q in quads for p in q]
    ys = [p[1] for q in quads for p in q]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) or 1.0

    def project(p: _Vec3) -> tuple[float, float]:
        nx = (p[0] - (minx + maxx) / 2) / span + 0.5
        ny = (p[1] - (miny + maxy) / 2) / span + 0.5
        x = 100.0 * (_CY_PAD + (1 - 2 * _CY_PAD) * nx)
        y = 100.0 * (_CY_PAD + (1 - 2 * _CY_PAD) * (1 - ny))  # SVG y grows down
        return (x, y)

    return project


def _face_intensity(normal: _Vec3) -> float:
    """Lambert diffuse intensity for a face ``normal`` (a scalar multiplier)."""
    lx, ly, lz = _CY_LIGHT
    ln = math.sqrt(lx * lx + ly * ly + lz * lz) or 1.0
    diffuse = max(0.0, (normal[0] * lx + normal[1] * ly + normal[2] * lz) / ln)
    return min(1.15, 0.30 + 0.75 * diffuse)


def _mastery_rgb(mastery: float, is_core: bool) -> _Vec3:
    """Base colour for a spike: red when unmastered, green when mastered.

    Core subjects follow a concave curve (``m ** _CORE_MASTERY_EXP``), so they
    stay red for longer and only green near full mastery.
    """
    m = max(0.0, min(1.0, mastery))
    if is_core:
        m = m**_CORE_MASTERY_EXP
    hue = _HUE_RED + (_HUE_GREEN - _HUE_RED) * m
    return colorsys.hsv_to_rgb(hue, _MASTERY_SAT, _MASTERY_VAL)


def _rgb_hex(rgb: _Vec3, intensity: float = 1.0) -> str:
    """Convert float rgb to ``#rrggbb``, scaled by ``intensity`` and clamped."""
    return "#" + "".join(f"{min(255, int(255 * c * intensity)):02x}" for c in rgb)


def _nearest_tip(x: float, y: float, tips: tuple[tuple[float, float], ...]) -> int:
    """Index of the spike tip nearest the 2D point ``(x, y)``."""
    best_i, best_d = 0, float("inf")
    for i, (tx, ty) in enumerate(tips):
        d = (x - tx) ** 2 + (y - ty) ** 2
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def _detect_tips(faces: list[_Face], count: int) -> list[tuple[float, float]]:
    """Find the ``count`` outermost spike tips of the projected figure.

    Bins vertices by angle about the centroid, keeps the farthest per angle,
    takes radial local maxima, then the ``count`` strongest, well-separated ones,
    ordered clockwise from the top.
    """
    pts = [p for _, poly, _ in faces for p in poly]
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    bins = 720
    best: dict[int, tuple[float, float, float]] = {}
    for x, y in pts:
        ang = math.atan2(y - cy, x - cx)
        r = math.hypot(x - cx, y - cy)
        bi = int((ang + math.pi) / (2 * math.pi) * bins) % bins
        if bi not in best or r > best[bi][0]:
            best[bi] = (r, x, y)
    arr = [best.get(i, (0.0, cx, cy)) for i in range(bins)]
    win = int(bins * 0.03)
    maxima = [
        arr[i]
        for i in range(bins)
        if arr[i][0] >= 30.0
        and all(arr[i][0] >= arr[(i + d) % bins][0] for d in range(-win, win + 1))
    ]
    maxima.sort(key=lambda t: -t[0])
    picked: list[tuple[float, float, float]] = []
    for r, x, y in maxima:
        if all(math.hypot(x - px, y - py) > 10.0 for _, px, py in picked):
            picked.append((r, x, y))
        if len(picked) >= count:
            break
    # Defensive: if the geometry yielded fewer clear tips, pad on a circle.
    for i in range(len(picked), count):
        ang = math.radians(-90 + i * 360.0 / count)
        picked.append((0.0, cx + 40 * math.cos(ang), cy + 40 * math.sin(ang)))
    picked.sort(
        key=lambda t: (math.atan2(t[2] - cy, t[1] - cx) + math.pi / 2) % (2 * math.pi)
    )
    return [(x, y) for _, x, y in picked]


@functools.lru_cache(maxsize=1)
def _manifold_geometry() -> tuple[
    tuple[_ShadedFace, ...], tuple[tuple[float, float], ...]
]:
    """Build the manifold once: return ``(shaded_faces, spike_tip_positions)``.

    Collection-independent, so cached. Each face carries its 2D polygon, its
    Lambert-shaded (pre-brightness) rgb, and the index of the spike tip it sits
    nearest — so ``_manifold_svg`` can brighten each face by its subject's
    mastery without recomputing the geometry. Tips are in stage-percent
    coordinates, matching the SVG's ``0..100`` viewBox.
    """
    quads = _cy_quads()
    project = _cy_projector(quads)
    shaded: list[tuple[float, list[tuple[float, float]], float]] = []
    for corners in quads:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz), _ = corners
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / nl, ny / nl, nz / nl
        if nz < 0:  # face the normal toward the viewer for consistent shading
            nx, ny, nz = -nx, -ny, -nz
        depth = sum(p[2] for p in corners) / 4
        shaded.append(
            (depth, [project(p) for p in corners], _face_intensity((nx, ny, nz)))
        )
    shaded.sort(key=lambda f: f[0])  # painter's algorithm: far faces first

    tips = tuple(
        _detect_tips([(d, poly, "") for d, poly, _ in shaded], MANIFOLD_POINTS)
    )
    faces: list[_ShadedFace] = []
    for _depth, poly, inten in shaded:
        fx = sum(x for x, _ in poly) / len(poly)
        fy = sum(y for _, y in poly) / len(poly)
        faces.append((tuple(poly), inten, _nearest_tip(fx, fy, tips)))
    return tuple(faces), tips


def _manifold_svg(mastery: tuple[float, ...], core: tuple[bool, ...]) -> str:
    """Assemble the manifold SVG, colouring each face red→green by mastery."""
    faces, _ = _manifold_geometry()
    polys = []
    for poly, inten, spike in faces:
        color = _rgb_hex(_mastery_rgb(mastery[spike], core[spike]), inten)
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in poly)
        polys.append(
            f'<polygon points="{points}" fill="{color}" stroke="{color}" '
            'stroke-width="0.35"/>'
        )
    return (
        '<svg id="cy-svg" viewBox="0 0 100 100" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        + "".join(polys)
        + "</svg>"
    )


def _point_positions() -> list[tuple[float, float]]:
    """(left%, top%) for each spike button, on the manifold's actual spike tips."""
    _, tips = _manifold_geometry()
    return [(50.0 + (x - 50.0) * _INWARD, 50.0 + (y - 50.0) * _INWARD) for x, y in tips]


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
        name = item.name.replace("\x1f", "::")
        # The Speed Recall formula deck (and its subject subdecks) has its own
        # entry point (the ⚡ bottom-bar button), so it isn't a manifold spike.
        if name == SPEED_RECALL_DECK or name.startswith(f"{SPEED_RECALL_DECK}::"):
            continue
        if did in seen or item.name == PGRE_PARENT:
            continue
        entries.append((did, item.name.split("::")[-1]))
    return entries


def page_count(col: Collection) -> int:
    """Number of manifold depths needed to show every deck (at least 1)."""
    decks = len(_display_decks(col))
    return max(1, math.ceil(decks / DECKS_PER_PAGE))


def _core_deck_ids(col: Collection) -> set[int]:
    """Deck ids of the three core subjects (Classical, EM, Quantum), if present."""
    ids: set[int] = set()
    for subject in SUBJECTS[:3]:
        deck = col.decks.by_name(subject.deck_name)
        if deck is not None:
            ids.add(int(deck["id"]))
    return ids


def _deck_mastery(col: Collection, deck_id: int) -> float:
    """Fraction of a deck's cards (incl. subdecks) that are mature (>= 21d ivl).

    A cheap mastery proxy for colouring the manifold: 0.0 for an empty or
    all-new deck, 1.0 when every card has reached a mature interval.
    """
    ids = ",".join(str(int(d)) for d in col.decks.deck_and_child_ids(DeckId(deck_id)))
    total, mature = col.db.first(
        f"select count(), coalesce(sum(ivl >= {_MATURE_IVL_DAYS}), 0) "
        f"from cards where did in ({ids})"
    )
    return mature / total if total else 0.0


def _spike_mastery(
    col: Collection, page: list[tuple[int, str]], core_ids: set[int]
) -> tuple[tuple[float, ...], tuple[bool, ...]]:
    """Per-spike ``(mastery, is_core)`` used to colour the manifold red→green.

    Empty spikes and the "More decks" spike stay at mastery 0 (red), so a fresh
    manifold is entirely red and greens only where the student masters a subject.
    The three core subjects are flagged so they stay red for longer.
    """
    mastery = [0.0] * MANIFOLD_POINTS
    core = [False] * MANIFOLD_POINTS
    for index, (deck_id, _label) in enumerate(page[:DECKS_PER_PAGE]):
        mastery[index] = _deck_mastery(col, deck_id)
        core[index] = deck_id in core_ids
    return tuple(mastery), tuple(core)


def build_manifold_html(col: Collection, depth: int = 0) -> str:
    """Return the home-screen HTML: the manifold SVG + 10 spike-buttons.

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
        # ``data-cx``/``data-cy`` record the spike's base position; dragging the
        # manifold orbits each button about the centre to keep it on its spike.
        pos = (
            f"style='left:{left:.2f}%;top:{top:.2f}%' "
            f"data-cx='{left:.2f}' data-cy='{top:.2f}'"
        )
        if index >= DECKS_PER_PAGE:
            # The final spike advances to the next page of decks.
            buttons.append(
                f"<button class='cy-point cy-more' {pos} "
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
            f"<button class='cy-point' {pos} "
            f"onclick=\"pycmd('open:{did}')\">"
            f"<span class='cy-num'>{start + index + 1}</span>{label}</button>"
        )

    if pages > 1:
        page_info = (
            f"Depth {depth} — decks {start + 1}–{start + len(page)} of {len(entries)}"
        )
    else:
        page_info = ""

    mastery, core = _spike_mastery(col, page, _core_deck_ids(col))
    svg = _manifold_svg(mastery, core)
    return (
        _MANIFOLD_BODY.format(
            svg=svg,
            buttons="\n".join(buttons),
            page_info=html.escape(page_info),
        )
        + _MANIFOLD_SCRIPT
    )


#: Inline styles + markup for the manifold screen. Kept self-contained so no
#: extra build rule (scss compile) is needed for the home screen.
_MANIFOLD_BODY = """
<style>
  #cy-wrap {{ text-align: center; position: relative; padding-top: 6px; }}
  /* faint physics-operator watermark behind the header (.pg-watermark supplies
     the mono font / faint colour; we only position it here). */
  #cy-headmark {{
    top: 2px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 46px;
    white-space: nowrap;
    z-index: 0;
  }}
  #cy-eyebrow {{ position: relative; z-index: 1; margin: 14px 0 6px; }}
  #cy-title {{
    position: relative;
    z-index: 1;
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 2px 0 4px;
    color: var(--pg-text);
  }}
  #cy-sub {{
    position: relative;
    z-index: 1;
    font-size: 13px;
    color: var(--pg-text-dim);
    margin-bottom: 2px;
  }}
  #cy-page {{
    font-family: var(--pg-mono);
    font-size: 12px;
    color: var(--pg-text-faint);
    margin-bottom: 6px;
    min-height: 1em;
  }}
  #cy-stage {{
    position: relative;
    width: min(84vmin, 820px);
    aspect-ratio: 1 / 1;
    margin: 0 auto;
    overflow: visible;
    cursor: grab;
    touch-action: none;
    z-index: 1;
  }}
  /* soft procedural bloom halo behind the manifold (no image) */
  #cy-stage::before {{
    content: "";
    position: absolute;
    inset: 6%;
    border-radius: 50%;
    background: radial-gradient(circle at 50% 50%, var(--pg-accent-glow) 0%, transparent 62%);
    filter: blur(28px);
    opacity: 0.45;
    z-index: -1;
    pointer-events: none;
  }}
  #cy-stage.cy-drag {{ cursor: grabbing; }}
  #cy-svg {{
    width: 100%;
    height: 100%;
    position: absolute;
    inset: 0;
    overflow: visible;
    transform-origin: 50% 50%;
    user-select: none;
    pointer-events: none;
  }}
  /* Spikes are dim luminous nodes by default; only :hover / .cy-active lights
     up cyan with a halo. */
  .cy-point {{
    position: absolute;
    transform: translate(-50%, -50%);
    max-width: 132px;
    padding: 6px 11px;
    border-radius: var(--pg-pill);
    border: 1px solid var(--pg-line);
    background: var(--pg-panel);
    color: var(--pg-text);
    font: inherit;
    font-size: 12.5px;
    line-height: 1.15;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    -webkit-backdrop-filter: blur(6px);
    backdrop-filter: blur(6px);
    transition: transform 0.12s ease, background 0.12s ease,
      border-color 0.12s ease, box-shadow 0.12s ease;
  }}
  .cy-point:hover,
  .cy-point.cy-active {{
    background: color-mix(in srgb, var(--pg-accent) 22%, var(--pg-panel-2));
    border-color: var(--pg-accent);
    box-shadow: var(--pg-glow);
    transform: translate(-50%, -50%) scale(1.06);
  }}
  .cy-num {{
    display: inline-block;
    min-width: 1.2em;
    margin-right: 5px;
    font-family: var(--pg-mono);
    font-weight: 700;
    color: var(--pg-text-dim);
  }}
  .cy-more {{
    border-style: dashed;
    border-color: var(--pg-line-strong);
    color: var(--pg-text-dim);
  }}
  .cy-more:hover {{
    background: color-mix(in srgb, var(--pg-accent) 18%, var(--pg-panel-2));
    border-color: var(--pg-accent);
    color: var(--pg-text);
  }}
  #cy-classic {{ margin-top: 14px; }}
  #cy-classic a {{
    cursor: pointer;
    text-decoration: underline;
    color: var(--pg-text-dim);
  }}
  #cy-classic a:hover {{ color: var(--pg-text); }}
  /* Centre button: launches the real-exam MCQ (Performance) quiz. It carries
     data-cx/cy=50 so the orbit script pivots it about the centre — i.e. it stays
     put while the manifold spins around it. This is the ONE glowing cyan core:
     the single loud element on the screen.

     It is a plain glowing circle. Its RADIUS is the distance from the manifold's
     centre of rotation (50,50) to the manifold's visual crossing "throat" — the
     point where the surface's fold seams converge, which the fixed view rotation
     places at ~(47.5, 55.5), i.e. ~6.5% of the stage off-centre (NOT at the
     rotation centre). Sizing the circle so width = 2 x that offset puts the
     intersection point exactly on the rim; because the button stays centred
     while the manifold spins, that point rides the rim at every angle. Width is
     in % of the square #cy-stage so the rim keeps tracking the throat as the
     stage resizes. */
  .cy-center {{
    max-width: none;
    width: 13%; /* diameter = 2 x 6.5% intersection-point offset */
    height: 13%;
    padding: 0;
    /* Force a TRUE circle. border-radius:50% was rendering as a rounded square
       here, so use an absolute pill radius on the square box instead. */
    border-radius: 9999px;
    /* .cy-point sets backdrop-filter: blur(); QtWebEngine clips that blur to the
       square border-box (ignoring the radius), leaving a square halo behind the
       disc. The core has its own gradient + box-shadow glow, so drop the blur. */
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    border: 1.5px solid var(--pg-accent);
    background: radial-gradient(circle at 50% 38%,
      color-mix(in srgb, var(--pg-accent) 34%, var(--pg-panel)) 0%,
      color-mix(in srgb, var(--pg-accent) 14%, var(--pg-panel-2)) 68%,
      var(--pg-panel-2) 100%);
    color: var(--pg-text);
    box-shadow: 0 0 18px var(--pg-accent-glow),
      inset 0 0 14px color-mix(in srgb, var(--pg-accent) 20%, transparent);
    overflow: visible;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: cy-core-pulse 3.4s ease-in-out infinite;
  }}
  .cy-center:hover {{
    background: radial-gradient(circle at 50% 38%,
      color-mix(in srgb, var(--pg-accent) 48%, var(--pg-panel)) 0%,
      color-mix(in srgb, var(--pg-accent) 22%, var(--pg-panel-2)) 68%,
      var(--pg-panel-2) 100%);
    box-shadow: 0 0 30px var(--pg-accent), 0 0 52px var(--pg-accent-glow);
    transform: translate(-50%, -50%) scale(1.05);
  }}
  .cy-center-label {{
    font-family: var(--pg-mono);
    font-size: 11px;
    line-height: 1.2;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    text-align: center;
    color: var(--pg-text);
    padding: 0 8px;
    pointer-events: none;
  }}
  .cy-center:hover .cy-center-label {{ color: #eafcff; }}
  @keyframes cy-core-pulse {{
    0%, 100% {{
      box-shadow: 0 0 18px var(--pg-accent-glow),
        inset 0 0 14px color-mix(in srgb, var(--pg-accent) 20%, transparent);
    }}
    50% {{
      box-shadow: 0 0 30px var(--pg-accent-glow), 0 0 46px var(--pg-accent-glow),
        inset 0 0 16px color-mix(in srgb, var(--pg-accent) 26%, transparent);
    }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .cy-center {{ animation: none; }}
  }}
</style>
<div id="cy-wrap">
  <div id="cy-headmark" class="pg-watermark" aria-hidden="true">ℏ ∮ ∇ ψ ∂ℒ/∂q</div>
  <div id="cy-eyebrow" class="pg-eyebrow">ANKIMATTER · CALABI–YAU</div>
  <div id="cy-title">Ankimatter</div>
  <div id="cy-sub">Making the physics GRE as easy as \\(\\sum \\vec{{F}} = 0 \\Rightarrow \\Delta\\vec{{v}} = 0\\), \\(\\vec{{F}} = m\\vec{{a}}\\), \\(\\vec{{F}}_{{12}} = -\\vec{{F}}_{{21}}\\)</div>
  <div id="cy-page">{page_info}</div>
  <div id="cy-stage">
    {svg}
    {buttons}
    <button class="cy-point cy-center" style="left:50%;top:50%"
            data-cx="50" data-cy="50" onclick="pycmd('mcq')"
            aria-label="Practice MCQs — real Physics GRE questions with AI coaching"
            title="Practice real Physics GRE exam questions with AI heuristic coaching">
      <span class="cy-center-label">Practice MCQs</span>
    </button>
  </div>
  <div id="cy-classic">
    <a onclick="pycmd('classic')">Classic deck list</a>
  </div>
</div>
"""

#: Drag-to-rotate behaviour for the manifold. Appended verbatim (not
#: ``format``-ed, so its braces need no escaping). Spinning is a pure in-plane
#: rotation: the SVG is rotated with a CSS transform and every button is orbited
#: about the centre by the same angle, so each button stays on its spike (and
#: stays upright). Grab anywhere on the manifold background to spin it; clicks on
#: the deck buttons still fall through to open the deck.
_MANIFOLD_SCRIPT = """
<script>
// Opt this page into the Observatory cosmic backdrop (pgre.css styles
// body.pg-observatory). stdHtml sets the <body> class itself, so we add ours
// here rather than in the body markup.
document.body.classList.add("pg-observatory");

(function () {
  var stage = document.getElementById("cy-stage");
  var svg = document.getElementById("cy-svg");
  if (!stage || !svg) { return; }
  var rot = 0;

  function place() {
    svg.style.transform = "rotate(" + rot + "deg)";
    var a = rot * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
    var pts = stage.querySelectorAll(".cy-point");
    for (var i = 0; i < pts.length; i++) {
      var el = pts[i];
      var dx = parseFloat(el.getAttribute("data-cx")) - 50;
      var dy = parseFloat(el.getAttribute("data-cy")) - 50;
      el.style.left = (50 + dx * ca - dy * sa).toFixed(2) + "%";
      el.style.top = (50 + dx * sa + dy * ca).toFixed(2) + "%";
    }
  }
  place();

  var dragging = false, lastAng = 0;
  function angleFrom(e) {
    var r = stage.getBoundingClientRect();
    return Math.atan2(e.clientY - (r.top + r.height / 2),
                      e.clientX - (r.left + r.width / 2));
  }
  stage.addEventListener("pointerdown", function (e) {
    if (e.target.closest && e.target.closest(".cy-point")) { return; }
    dragging = true;
    lastAng = angleFrom(e);
    stage.classList.add("cy-drag");
    try { stage.setPointerCapture(e.pointerId); } catch (err) {}
    e.preventDefault();
  });
  stage.addEventListener("pointermove", function (e) {
    if (!dragging) { return; }
    var a = angleFrom(e);
    rot += (a - lastAng) * 180 / Math.PI;
    lastAng = a;
    place();
  });
  function endDrag() { dragging = false; stage.classList.remove("cy-drag"); }
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);
})();

// Render the LaTeX in the subtitle. MathJax loads async and is configured with
// startup.typeset:false, so wait until it's ready, then typeset once.
(function typeset() {
  if (globalThis.MathJax && MathJax.startup && MathJax.startup.promise) {
    MathJax.startup.promise.then(function () { MathJax.typesetPromise(); });
  } else {
    setTimeout(typeset, 50);
  }
})();
</script>
"""
