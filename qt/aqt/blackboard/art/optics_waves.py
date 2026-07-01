# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Optics & Waves board."""

TAGLINE = "n₁ sinθ₁ = n₂ sinθ₂"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- converging lens ray diagram, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 18 132 Q 120 129 232 132" stroke="#f0ead6" stroke-width="2" stroke-dasharray="9 6" fill="none"/>
    <path d="M 125 52 Q 144 130 125 210 Q 106 130 125 52 Z" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 57 130 Q 58 108 57 90" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 57 90 l -6 9 m 6 -9 l 6 9" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 57 88 Q 91 86 125 88 L 197 178" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 57 88 Q 126 133 197 178" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 57 88 L 125 178 Q 161 180 197 178" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 197 134 Q 196 156 197 172" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 197 178 l -6 -9 m 6 9 l 6 -9" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <circle cx="160" cy="132" r="4" stroke="none" fill="#ffd9a0"/>
    <circle cx="90" cy="132" r="4" stroke="none" fill="#ffd9a0"/>
    <text x="164" y="122" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">F</text>
    <text x="78" y="122" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">F</text>
    <text x="36" y="248" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">1/f = 1/o + 1/i</text>
  </g>

  <!-- snell's law refraction, top-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 788 132 Q 888 128 986 132" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 886 44 Q 887 132 886 222" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 7" fill="none"/>
    <path d="M 802 58 Q 844 94 886 132" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 862 110 l 2 10 m -2 -10 l 10 -1" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 886 132 Q 910 174 932 218" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <path d="M 932 218 l -9 -4 m 9 4 l -2 -10" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 886 98 Q 872 101 861 111" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 886 168 Q 897 166 905 158" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <text x="842" y="92" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffc4c4">θ₁</text>
    <text x="906" y="188" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffc4c4">θ₂</text>
    <text x="942" y="112" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#bfe3ff">n₁</text>
    <text x="942" y="172" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#bfe3ff">n₂</text>
  </g>

  <!-- young's double slit with fringes, bottom-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 32 378 Q 31 450 32 522" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 48 378 Q 49 450 48 522" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 64 378 Q 63 450 64 522" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 78 362 Q 79 386 78 408 M 78 424 Q 77 442 78 458 M 78 474 Q 79 506 78 538" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 78 402 A 14 14 0 0 1 78 430 M 78 388 A 28 28 0 0 1 78 444 M 78 374 A 42 42 0 0 1 78 458" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 78 452 A 14 14 0 0 1 78 480 M 78 438 A 28 28 0 0 1 78 494 M 78 424 A 42 42 0 0 1 78 508" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 196 366 Q 197 452 196 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 199 372 Q 212 380 199 388 Q 206 396 199 404 Q 218 414 199 424 Q 228 441 199 458 Q 218 468 199 478 Q 206 486 199 494 Q 212 502 199 510" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <text x="30" y="556" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#ffd9a0">d sinθ = mλ</text>
  </g>

  <!-- prism splitting light into a spectrum, bottom-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 845 532 Q 872 486 902 438 Q 930 486 958 532 Q 902 535 845 532" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 780 466 Q 826 476 872 486" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 872 486 Q 897 489 922 492" stroke="#f0ead6" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <path d="M 922 492 Q 957 476 992 458" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 922 492 Q 958 486 994 478" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <path d="M 922 492 Q 958 496 994 498" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 922 492 Q 956 506 990 518" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <text x="864" y="556" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">n(λ)</text>
  </g>

  <!-- standing wave on a string, bottom edge -->
  <g opacity="0.32" stroke-linecap="round">
    <path d="M 292 470 Q 293 508 292 544" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 292 480 l -8 -8 M 292 504 l -8 -8 M 292 528 l -8 -8" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 708 470 Q 707 508 708 544" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 708 480 l 8 -8 M 708 504 l 8 -8 M 708 528 l 8 -8" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 296 508 Q 399 452 502 508 Q 605 564 706 508" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <path d="M 296 508 Q 399 564 502 508 Q 605 452 706 508" stroke="#bfe3ff" stroke-width="2" stroke-dasharray="5 6" fill="none"/>
    <circle cx="296" cy="508" r="4" stroke="none" fill="#ffd9a0"/>
    <circle cx="502" cy="508" r="4" stroke="none" fill="#ffd9a0"/>
    <circle cx="706" cy="508" r="4" stroke="none" fill="#ffd9a0"/>
    <text x="366" y="492" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">λ/2</text>
  </g>

  <!-- chalk formulas along the top edge -->
  <g opacity="0.42">
    <text x="430" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#ffd9a0">v = fλ</text>
    <text x="546" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#bfe3ff">c = λν</text>
  </g>
</svg>"""
