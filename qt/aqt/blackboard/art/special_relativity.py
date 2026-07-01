# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Special Relativity board."""

TAGLINE = "c is the same for everyone"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Minkowski diagram with boosted frame, top-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 110 208 Q 108 120 110 34" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 110 34 l -6 10 m 6 -10 l 7 10" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 110 208 Q 158 206 206 208" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 206 208 l -10 -6 m 10 6 l -10 7" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 110 208 Q 152 165 196 122" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="7 7" fill="none"/>
    <path d="M 110 208 Q 69 165 26 122" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="7 7" fill="none"/>
    <path d="M 110 208 Q 132 120 138 44" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 138 44 l -8 8 m 8 -8 l 4 11" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 110 208 Q 156 194 202 182" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 202 182 l -11 -2 m 11 2 l -9 8" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 110 208 Q 122 160 114 120 Q 106 84 122 48" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <text x="88" y="46" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">ct</text>
    <text x="192" y="230" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">x</text>
    <text x="146" y="40" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">ct&#8242;</text>
    <text x="196" y="170" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">x&#8242;</text>
    <text x="164" y="106" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffd9a0">future</text>
    <text x="34" y="242" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffd9a0">past</text>
  </g>

  <!-- Lorentz factor curve, top-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 806 206 Q 804 124 806 42" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 806 42 l -6 10 m 6 -10 l 7 10" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 806 206 Q 890 204 974 206" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 974 206 l -10 -6 m 10 6 l -10 7" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 946 204 Q 948 128 946 52" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7" fill="none"/>
    <path d="M 808 186 Q 870 182 906 160 Q 934 140 944 66" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <text x="786" y="52" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">&#947;</text>
    <text x="940" y="228" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#ffd9a0">v/c = 1</text>
    <text x="788" y="192" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#bfe3ff">1</text>
    <text x="856" y="228" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">v/c</text>
  </g>

  <!-- time dilation clocks, bottom-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <circle cx="80" cy="452" r="40" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 80 418 l 0 7 M 80 486 l 0 -7 M 46 452 l 7 0 M 114 452 l -7 0" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 80 452 L 80 426 M 80 452 L 98 462" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <text x="72" y="522" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">t</text>
    <ellipse cx="182" cy="456" rx="24" ry="40" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 182 422 l 0 7 M 182 490 l 0 -7 M 162 456 l 6 0 M 202 456 l -6 0" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 182 456 L 182 432 M 182 456 L 172 466" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <text x="172" y="524" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#ffc4c4">t&#8242;</text>
    <path d="M 128 400 Q 130 428 128 456 M 140 396 Q 142 430 140 462" stroke="#c8f0c8" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <text x="36" y="556" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#c8f0c8">&#916;t&#8242; = &#947;&#916;t</text>
  </g>

  <!-- contracted rocket with v arrow, bottom-right corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 826 452 Q 828 430 852 424 L 928 424 Q 958 434 966 452 Q 958 470 928 480 L 852 480 Q 828 474 826 452 Z" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 852 424 Q 838 406 826 398 L 848 424 M 852 480 Q 838 498 826 506 L 848 480" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="906" cy="452" r="10" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 796 436 Q 780 438 764 436 M 800 452 Q 778 454 756 452 M 796 468 Q 780 470 764 468" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 880 402 Q 916 400 950 402" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 950 402 l -10 -6 m 10 6 l -10 7" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="922" y="392" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">v</text>
    <path d="M 838 508 Q 898 505 958 508" stroke="#c8f0c8" stroke-width="2" stroke-dasharray="6 6" fill="none"/>
    <path d="M 838 502 l 0 12 M 958 502 l 0 12" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <text x="856" y="534" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">L = L&#8320;/&#947;</text>
  </g>

  <!-- chalk formulas along top and bottom edges -->
  <g opacity="0.42">
    <text x="380" y="40" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#ffd9a0">E = mc&#178;</text>
    <text x="530" y="40" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="20" fill="#bfe3ff">&#947; = 1/&#8730;(1&#8722;&#946;&#178;)</text>
    <text x="400" y="550" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">x&#8242; = &#947;(x &#8722; vt),  s&#178; = (ct)&#178; &#8722; x&#178;</text>
  </g>
</svg>"""
