# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Atomic Physics board."""

TAGLINE = "1/λ = R(1/n₁² − 1/n₂²)"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Bohr atom, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <circle cx="105" cy="130" r="8" fill="#ffd9a0" stroke="none"/>
    <ellipse cx="105" cy="130" rx="34" ry="31" fill="none" stroke="#bfe3ff" stroke-width="2.5" stroke-dasharray="7 6"/>
    <ellipse cx="105" cy="130" rx="60" ry="57" fill="none" stroke="#bfe3ff" stroke-width="2.5" stroke-dasharray="8 7"/>
    <ellipse cx="105" cy="130" rx="87" ry="83" fill="none" stroke="#bfe3ff" stroke-width="2.5" stroke-dasharray="9 8"/>
    <circle cx="163" cy="115" r="5" fill="#c8f0c8" stroke="none"/>
    <circle cx="60" cy="200" r="5" fill="#c8f0c8" stroke="none"/>
    <!-- electron jump from outer to middle orbit -->
    <path d="M 160 118 Q 148 128 141 143" fill="none" stroke="#c8f0c8" stroke-width="2" stroke-dasharray="4 5"/>
    <!-- emitted photon squiggle, heading down the left edge -->
    <path d="M 128 215 q -13 11 -1 22 q 12 11 -1 22 q -13 11 -1 22 q 12 11 -1 22" fill="none" stroke="#ffd9a0" stroke-width="3"/>
    <path d="M 116 288 L 124 303 L 134 290" fill="none" stroke="#ffd9a0" stroke-width="3"/>
    <text x="140" y="270" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="26" fill="#ffd9a0">hν</text>
    <text x="42" y="330" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#f0ead6">E = hν</text>
  </g>

  <!-- fine-structure splitting, along the top edge -->
  <g opacity="0.32" stroke-linecap="round">
    <path d="M 380 40 q 20 -2 42 0 q 20 2 40 0" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 470 40 Q 486 34 502 33" fill="none" stroke="#f0ead6" stroke-width="2" stroke-dasharray="4 4"/>
    <path d="M 470 40 Q 486 46 502 48" fill="none" stroke="#f0ead6" stroke-width="2" stroke-dasharray="4 4"/>
    <path d="M 505 32 q 22 2 46 1" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <path d="M 505 49 q 22 -2 46 -1" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <text x="562" y="46" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="19" fill="#ffc4c4">fine structure</text>
  </g>

  <!-- hydrogen energy ladder, right edge -->
  <g opacity="0.42" stroke-linecap="round">
    <text x="812" y="120" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="23" fill="#f0ead6">Eₙ = −13.6 eV/n²</text>
    <path d="M 825 150 q 30 -2 62 0 q 30 2 63 0" fill="none" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 6"/>
    <path d="M 825 192 q 30 2 62 0 q 30 -2 63 1" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 825 232 q 30 -2 62 1 q 30 2 63 -1" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 825 302 q 30 2 62 -1 q 30 -2 63 1" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 825 442 q 30 -2 62 0 q 30 2 63 0" fill="none" stroke="#f0ead6" stroke-width="3"/>
    <text x="957" y="157" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="19" fill="#f0ead6">∞</text>
    <text x="957" y="199" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">n=4</text>
    <text x="957" y="239" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">n=3</text>
    <text x="957" y="309" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">n=2</text>
    <text x="957" y="449" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">n=1</text>
    <!-- Lyman series (to n=1), blue -->
    <path d="M 843 306 q 3 45 -1 90 q -2 22 0 42" fill="none" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M 835 424 L 842 438 L 850 425" fill="none" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M 862 236 q -3 68 1 135 q 2 33 -1 67" fill="none" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M 854 424 L 862 438 L 870 425" fill="none" stroke="#bfe3ff" stroke-width="2.5"/>
    <text x="822" y="480" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#bfe3ff">Lyman</text>
    <!-- Balmer series (to n=2), pink -->
    <path d="M 903 236 q 3 20 -1 40 q -2 12 1 22" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <path d="M 895 284 L 903 298 L 911 285" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <path d="M 922 196 q -3 32 1 64 q 2 20 -1 38" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <path d="M 914 284 L 922 298 L 930 285" fill="none" stroke="#ffc4c4" stroke-width="2.5"/>
    <text x="890" y="335" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffc4c4">Balmer</text>
  </g>

  <!-- emission spectrum strip, bottom-left -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 42 462 q 78 -3 154 0 q 76 3 152 -1 l 2 62 q -76 3 -154 0 q -76 -3 -152 1 z" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 74 470 q 2 22 -1 45" fill="none" stroke="#ffc4c4" stroke-width="3.5"/>
    <path d="M 116 470 q -2 23 1 45" fill="none" stroke="#bfe3ff" stroke-width="3"/>
    <path d="M 178 470 q 2 22 -1 45" fill="none" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M 214 470 q -1 23 1 45" fill="none" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M 296 470 q 2 22 -1 45" fill="none" stroke="#ffd9a0" stroke-width="3"/>
    <text x="62" y="550" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffc4c4">Hα</text>
    <text x="222" y="550" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">emission lines</text>
  </g>

  <!-- photoelectric effect, bottom-right of center -->
  <g opacity="0.35" stroke-linecap="round">
    <path d="M 560 520 q 60 4 120 0 q 60 -4 118 1" fill="none" stroke="#f0ead6" stroke-width="3"/>
    <path d="M 585 522 L 570 538" fill="none" stroke="#f0ead6" stroke-width="2"/>
    <path d="M 630 522 L 615 538" fill="none" stroke="#f0ead6" stroke-width="2"/>
    <path d="M 675 522 L 660 538" fill="none" stroke="#f0ead6" stroke-width="2"/>
    <path d="M 720 522 L 705 538" fill="none" stroke="#f0ead6" stroke-width="2"/>
    <path d="M 765 522 L 750 538" fill="none" stroke="#f0ead6" stroke-width="2"/>
    <!-- incoming photon -->
    <path d="M 570 442 q 14 -8 18 6 q 4 14 18 6 q 14 -8 18 6 q 4 14 18 6 l 8 8" fill="none" stroke="#ffd9a0" stroke-width="3"/>
    <path d="M 636 500 L 653 514 L 656 494" fill="none" stroke="#ffd9a0" stroke-width="3"/>
    <text x="540" y="470" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#ffd9a0">hν</text>
    <!-- ejected electron -->
    <circle cx="700" cy="502" r="5" fill="#c8f0c8" stroke="none"/>
    <path d="M 708 496 Q 738 472 766 456" fill="none" stroke="#c8f0c8" stroke-width="2.5"/>
    <path d="M 748 456 L 768 454 L 758 472" fill="none" stroke="#c8f0c8" stroke-width="2.5"/>
    <text x="776" y="470" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="21" fill="#c8f0c8">e⁻</text>
  </g>
</svg>"""
