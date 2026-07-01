# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Laboratory Methods board."""

TAGLINE = "no measurement without an error bar"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- oscilloscope, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <rect x="34" y="34" width="176" height="150" rx="10" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <rect x="48" y="46" width="148" height="98" rx="6" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 85 50 Q 84 96 85 140 M 122 50 Q 123 96 122 140 M 159 50 Q 158 96 159 140" stroke="#bfe3ff" stroke-width="1.5" stroke-dasharray="3 6" fill="none"/>
    <path d="M 52 79 Q 122 77 192 79 M 52 111 Q 122 113 192 111" stroke="#bfe3ff" stroke-width="1.5" stroke-dasharray="3 6" fill="none"/>
    <path d="M 52 95 Q 59 58 66 95 Q 73 130 80 95 Q 87 66 94 95 Q 101 122 108 95 Q 114 74 120 95 Q 126 114 132 95 Q 138 81 144 95 Q 150 108 156 95 Q 162 86 168 95 Q 175 102 182 95 Q 187 91 192 95" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <circle cx="78" cy="164" r="9" stroke="#ffd9a0" stroke-width="2.5" fill="none"/>
    <path d="M 78 164 l 5 -6" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <circle cx="118" cy="164" r="9" stroke="#ffd9a0" stroke-width="2.5" fill="none"/>
    <path d="M 118 164 l -6 -4" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="146" y="171" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">trig</text>
    <text x="44" y="216" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="19" fill="#ffd9a0">V = IR</text>
  </g>

  <!-- gaussian bell curve, top-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 792 186 Q 884 183 976 186" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 798 184 C 842 181 856 58 884 58 C 912 58 926 181 970 184" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 884 62 Q 885 124 884 184" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="5 7" fill="none"/>
    <path d="M 850 108 Q 851 146 850 184 M 918 108 Q 917 146 918 184" stroke="#ffc4c4" stroke-width="2" stroke-dasharray="4 7" fill="none"/>
    <path d="M 856 168 Q 884 160 912 168" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 856 168 l 8 -5 m -8 5 l 9 3 M 912 168 l -8 -5 m 8 5 l -9 3" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <text x="866" y="150" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">68%</text>
    <text x="878" y="206" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#ffd9a0">μ</text>
    <text x="838" y="206" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">−σ</text>
    <text x="912" y="206" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">+σ</text>
    <text x="808" y="238" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">σ_x̄ = σ/√N</text>
  </g>

  <!-- scatter plot with error bars and fit line, bottom-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 50 362 Q 48 445 50 528" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 50 362 l -6 9 m 6 -9 l 6 9" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 50 528 Q 142 531 234 528" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 234 528 l -9 -6 m 9 6 l -9 6" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 78 492 l 0 24 m -5 -24 l 10 0 m -10 24 l 10 0" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="78" cy="504" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 108 474 l 0 22 m -5 -22 l 10 0 m -10 22 l 10 0" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="108" cy="485" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 138 462 l 0 26 m -5 -26 l 10 0 m -10 26 l 10 0" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="138" cy="475" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 168 438 l 0 22 m -5 -22 l 10 0 m -10 22 l 10 0" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="168" cy="449" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 198 420 l 0 24 m -5 -24 l 10 0 m -10 24 l 10 0" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="198" cy="432" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 60 518 Q 140 472 226 414" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <text x="222" y="548" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">x</text>
    <text x="32" y="376" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">y</text>
    <text x="64" y="398" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">y = mx + b</text>
  </g>

  <!-- log-log plot, bottom-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 800 388 Q 798 458 800 528" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 800 388 l -6 9 m 6 -9 l 6 9" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 800 528 Q 886 531 972 528" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 972 528 l -9 -6 m 9 6 l -9 6" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 830 528 l 0 8 M 848 528 l 0 5 M 858 528 l 0 5 M 878 528 l 0 8 M 896 528 l 0 5 M 906 528 l 0 5 M 926 528 l 0 8 M 944 528 l 0 5 M 954 528 l 0 5" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 800 498 l -8 0 M 800 480 l -5 0 M 800 470 l -5 0 M 800 450 l -8 0 M 800 432 l -5 0 M 800 422 l -5 0" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 812 514 Q 884 468 962 408" stroke="#ffd9a0" stroke-width="2.5" fill="none"/>
    <text x="852" y="446" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">slope = n</text>
    <text x="912" y="550" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">log x</text>
    <text x="806" y="404" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">log y</text>
  </g>

  <!-- ruler along bottom edge -->
  <g opacity="0.34" stroke-linecap="round">
    <path d="M 300 500 Q 460 496 620 500" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 300 536 Q 460 540 620 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 300 500 Q 299 518 300 536 M 620 500 Q 621 518 620 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 330 500 l 0 14 M 360 499 l 0 9 M 390 498 l 0 9 M 420 498 l 0 14 M 450 497 l 0 9 M 480 497 l 0 9 M 510 497 l 0 14 M 540 498 l 0 9 M 570 498 l 0 9 M 600 499 l 0 14" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="404" y="530" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffd9a0">1</text>
    <text x="494" y="530" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffd9a0">2</text>
    <text x="636" y="524" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#bfe3ff">cm</text>
  </g>

  <!-- chalk formulas along top and bottom edges -->
  <g opacity="0.4">
    <text x="408" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#c8f0c8">x ± δx</text>
    <text x="524" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="21" fill="#bfe3ff">χ² = Σ(O−E)²/E</text>
    <text x="292" y="560" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffc4c4">systematic ≠ statistical</text>
  </g>
</svg>"""
