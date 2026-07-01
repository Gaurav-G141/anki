# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Specialized Topics board."""

TAGLINE = "quarks, crystals, and everything in between"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- feynman diagram: e- e+ annihilation, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 34 40 Q 76 74 116 110" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 70 68 l 12 2 m -12 -2 l 2 12" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 34 182 Q 76 148 116 112" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 82 140 l -2 -12 m 2 12 l -12 -2" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <circle cx="118" cy="111" r="4" stroke="none" fill="#ffd9a0"/>
    <path d="M 122 111 q 8 -16 17 -1 q 8 16 17 1 q 8 -16 17 -1 q 8 16 17 1 q 8 -16 17 -1" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <text x="24" y="30" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">e⁻</text>
    <text x="24" y="208" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#f0ead6">e⁺</text>
    <text x="214" y="102" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">γ</text>
  </g>

  <!-- crystal lattice with springs, top-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 812 46 Q 842 42 866 46 M 878 46 Q 906 50 930 46" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 812 108 Q 842 112 866 108 M 878 108 Q 906 104 930 108" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 812 170 Q 842 166 866 170 M 878 170 Q 906 174 930 170" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 806 52 Q 802 76 806 102 M 806 114 Q 810 140 806 164" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 872 52 Q 876 76 872 102 M 872 114 Q 868 140 872 164" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 936 52 Q 932 76 936 102 M 936 114 Q 940 140 936 164" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <circle cx="806" cy="46" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="872" cy="46" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="936" cy="46" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="806" cy="108" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="872" cy="108" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="936" cy="108" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="806" cy="170" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="872" cy="170" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="936" cy="170" r="8" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 872 196 l 6 -6 m -6 6 l 6 6 M 872 196 Q 904 194 936 196 M 936 196 l -6 -6 m 6 6 l -6 6" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="898" y="220" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">a</text>
  </g>

  <!-- alpha decay, bottom-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <circle cx="82" cy="452" r="11" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <circle cx="104" cy="446" r="11" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <circle cx="94" cy="468" r="11" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <circle cx="116" cy="464" r="11" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <circle cx="70" cy="472" r="11" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <circle cx="92" cy="488" r="11" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <circle cx="114" cy="486" r="11" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 134 456 Q 158 444 182 434" stroke="#ffc4c4" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <path d="M 182 434 l -10 0 m 10 0 l -3 10" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <circle cx="198" cy="422" r="7" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <circle cx="212" cy="418" r="7" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <circle cx="200" cy="436" r="7" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <circle cx="214" cy="432" r="7" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <text x="222" y="408" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#c8f0c8">α</text>
    <text x="34" y="530" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">N(t) = N₀e^(−λt)</text>
    <text x="52" y="556" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">t½ = ln2 / λ</text>
  </g>

  <!-- band structure with gap, bottom-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 812 548 Q 810 480 812 412 M 812 412 l -5 9 m 5 -9 l 5 9" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 806 544 Q 886 546 966 544 M 966 544 l -9 -5 m 9 5 l -9 5" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 826 424 Q 888 470 954 426" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 826 534 Q 888 490 954 532" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 890 462 Q 889 476 890 500" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="2 5" fill="none"/>
    <text x="900" y="486" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">Eg</text>
    <text x="920" y="418" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#bfe3ff">cond.</text>
    <text x="920" y="524" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffc4c4">val.</text>
    <text x="790" y="406" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">E</text>
  </g>

  <!-- beta decay arrows along right edge -->
  <g opacity="0.34" stroke-linecap="round">
    <circle cx="948" cy="284" r="12" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 934 292 Q 908 306 884 322 M 884 322 l 10 -1 m -10 1 l 4 -9" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 944 298 Q 936 326 930 352 M 930 352 l 7 -7 m -7 7 l -3 -9" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <text x="862" y="316" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">e⁻</text>
    <text x="938" y="374" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">ν̄</text>
    <text x="906" y="264" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">β⁻</text>
  </g>

  <!-- chalk formulas along top and bottom edges -->
  <g opacity="0.42">
    <text x="424" y="40" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#ffd9a0">E = mc²</text>
    <text x="574" y="40" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="20" fill="#c8f0c8">n → p + e⁻ + ν̄</text>
    <text x="418" y="550" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#bfe3ff">nλ = 2d sinθ</text>
  </g>
</svg>"""
