# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Thermodynamics & Statistical Mechanics board."""

TAGLINE = "S = k log W"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Carnot cycle on a P-V diagram, top-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 48 40 Q 46 122 48 208" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 48 208 Q 128 210 212 208" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 48 40 l -5 9 m 5 -9 l 6 9 M 212 208 l -9 -5 m 9 5 l -9 6" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <text x="30" y="52" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">P</text>
    <text x="204" y="228" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">V</text>
    <path d="M 74 66 Q 108 74 138 96" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 138 96 Q 158 122 164 150" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 164 150 Q 132 148 100 132" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 100 132 Q 82 102 74 66" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 110 80 l 10 4 m -10 -4 l 8 -7" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 130 142 l -10 -3 m 10 3 l -8 6" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="142" y="76" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">T_H</text>
    <text x="150" y="182" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">T_C</text>
    <text x="56" y="246" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#c8f0c8">η = 1 − T_C/T_H</text>
  </g>

  <!-- heat-engine block diagram, top-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <rect x="828" y="34" width="132" height="44" rx="6" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <text x="852" y="63" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffc4c4">hot  T_H</text>
    <path d="M 892 80 Q 893 100 892 118" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 892 118 l -6 -8 m 6 8 l 6 -8" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="902" y="106" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">Q_H</text>
    <circle cx="892" cy="150" r="30" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <text x="882" y="157" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">E</text>
    <path d="M 862 150 Q 838 152 816 150" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <path d="M 816 150 l 9 -5 m -9 5 l 9 6" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <text x="806" y="140" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">W</text>
    <path d="M 892 180 Q 891 198 892 214" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 892 214 l -6 -8 m 6 8 l 6 -8" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <text x="902" y="204" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#bfe3ff">Q_C</text>
    <rect x="828" y="218" width="132" height="44" rx="6" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <text x="848" y="247" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#bfe3ff">cold  T_C</text>
  </g>

  <!-- Maxwell-Boltzmann speed distribution, bottom-left corner -->
  <g opacity="0.38" stroke-linecap="round">
    <path d="M 44 396 Q 42 464 44 532" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 44 532 Q 138 534 236 532" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 44 396 l -5 9 m 5 -9 l 6 9 M 236 532 l -9 -5 m 9 5 l -9 6" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 46 530 Q 70 460 88 448 Q 106 438 126 470 Q 150 508 224 528" stroke="#c8f0c8" stroke-width="3" fill="none"/>
    <path d="M 46 530 Q 86 494 118 484 Q 152 476 180 496 Q 204 514 230 524" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 90 448 Q 90 490 90 530" stroke="#f0ead6" stroke-width="2" stroke-dasharray="3 7" fill="none"/>
    <text x="98" y="440" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#c8f0c8">low T</text>
    <text x="186" y="482" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#ffd9a0">high T</text>
    <text x="200" y="552" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">v</text>
    <text x="26" y="410" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#f0ead6">n(v)</text>
  </g>

  <!-- piston-cylinder with gas dots, bottom-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 812 420 Q 810 478 812 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 952 420 Q 954 478 952 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 812 536 Q 882 539 952 536" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 810 452 Q 882 449 954 452" stroke="#ffd9a0" stroke-width="4" fill="none"/>
    <path d="M 882 444 Q 881 416 882 392" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 882 392 Q 881 380 882 370" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 882 370 l -6 9 m 6 -9 l 6 9" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <circle cx="840" cy="480" r="4" stroke="none" fill="#bfe3ff"/>
    <circle cx="872" cy="502" r="4" stroke="none" fill="#bfe3ff"/>
    <circle cx="908" cy="474" r="4" stroke="none" fill="#bfe3ff"/>
    <circle cx="930" cy="512" r="4" stroke="none" fill="#bfe3ff"/>
    <circle cx="856" cy="520" r="4" stroke="none" fill="#bfe3ff"/>
    <circle cx="898" cy="524" r="4" stroke="none" fill="#bfe3ff"/>
    <path d="M 908 474 l 14 -10 M 840 480 l -12 12 M 872 502 l 14 8" stroke="#bfe3ff" stroke-width="2" stroke-dasharray="1 5" fill="none"/>
    <text x="836" y="560" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#c8f0c8">PV = nRT</text>
  </g>

  <!-- entropy microstates doodle, bottom edge center -->
  <g opacity="0.32" stroke-linecap="round">
    <rect x="356" y="474" width="66" height="60" rx="4" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <circle cx="372" cy="490" r="3" stroke="none" fill="#c8f0c8"/>
    <circle cx="389" cy="490" r="3" stroke="none" fill="#c8f0c8"/>
    <circle cx="406" cy="490" r="3" stroke="none" fill="#c8f0c8"/>
    <circle cx="372" cy="506" r="3" stroke="none" fill="#c8f0c8"/>
    <circle cx="389" cy="506" r="3" stroke="none" fill="#c8f0c8"/>
    <circle cx="406" cy="506" r="3" stroke="none" fill="#c8f0c8"/>
    <path d="M 440 502 Q 490 496 542 502" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 542 502 l -10 -4 m 10 4 l -9 7" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="466" y="490" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">ΔS ≥ 0</text>
    <rect x="560" y="474" width="66" height="60" rx="4" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <circle cx="574" cy="486" r="3" stroke="none" fill="#ffc4c4"/>
    <circle cx="612" cy="494" r="3" stroke="none" fill="#ffc4c4"/>
    <circle cx="586" cy="522" r="3" stroke="none" fill="#ffc4c4"/>
    <circle cx="602" cy="480" r="3" stroke="none" fill="#ffc4c4"/>
    <circle cx="570" cy="508" r="3" stroke="none" fill="#ffc4c4"/>
    <circle cx="616" cy="516" r="3" stroke="none" fill="#ffc4c4"/>
  </g>

  <!-- chalk formulas along the top edge -->
  <g opacity="0.42">
    <text x="360" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#ffd9a0">dU = TdS − PdV</text>
    <text x="580" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="20" fill="#bfe3ff">⟨E⟩ = 3/2 kB T</text>
  </g>
</svg>"""
