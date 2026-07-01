# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Classical Mechanics board."""

TAGLINE = "F = ma — everything else is commentary"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- pendulum, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 40 32 Q 110 29 185 33" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 55 32 L 45 22 M 80 32 L 70 22 M 105 32 L 95 22 M 130 32 L 120 22 M 155 32 L 145 22 M 178 32 L 168 22" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 112 33 Q 111 100 110 172" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 7" fill="none"/>
    <path d="M 112 33 Q 92 95 66 152" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <circle cx="62" cy="161" r="12" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <path d="M 58 172 Q 108 192 160 170" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <path d="M 160 170 l -9 -2 m 9 2 l -6 7" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 112 62 Q 106 66 103 72" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <text x="94" y="58" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#ffc4c4">θ</text>
    <text x="72" y="102" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#bfe3ff">ℓ</text>
    <text x="34" y="218" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="19" fill="#f0ead6">T = 2π√(ℓ/g)</text>
  </g>

  <!-- kepler orbit, top-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <ellipse cx="880" cy="115" rx="96" ry="56" stroke="#f0ead6" stroke-width="3" fill="none" transform="rotate(-4 880 115)"/>
    <circle cx="952" cy="112" r="13" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 952 90 l 0 -10 M 952 134 l 0 10 M 930 112 l -10 0 M 974 112 l 10 0 M 937 97 l -8 -7 M 967 127 l 8 7 M 937 127 l -8 7 M 967 97 l 8 -7" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <path d="M 952 112 L 906 62 Q 875 57 846 66 Z" stroke="#c8f0c8" stroke-width="2" fill="#c8f0c8" fill-opacity="0.25"/>
    <circle cx="906" cy="62" r="5" stroke="none" fill="#bfe3ff"/>
    <path d="M 906 62 l 22 -6 m 0 0 l -8 -5 m 8 5 l -7 7" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <text x="856" y="98" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">dA/dt</text>
    <text x="812" y="205" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="19" fill="#f0ead6">τ = Iα</text>
  </g>

  <!-- inclined plane with block, bottom-left corner -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 32 522 Q 140 519 246 521" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 246 521 Q 145 452 36 382" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 36 382 Q 34 452 32 522" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 118 468 l 34 22 l 22 -30 l -34 -22 Z" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 146 452 Q 133 435 122 420" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <path d="M 122 420 l 0 10 m 0 -10 l 9 5" stroke="#bfe3ff" stroke-width="2" fill="none"/>
    <text x="100" y="414" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#bfe3ff">N</text>
    <path d="M 148 470 Q 149 494 150 516" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 150 516 l -5 -9 m 5 9 l 6 -8" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <text x="156" y="512" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffc4c4">mg</text>
    <path d="M 118 470 Q 96 456 76 442" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <path d="M 76 442 l 10 1 m -10 -1 l 3 9" stroke="#c8f0c8" stroke-width="2" fill="none"/>
    <text x="58" y="438" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#c8f0c8">f</text>
    <path d="M 208 521 Q 206 508 196 498" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="176" y="512" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">θ</text>
  </g>

  <!-- spring-mass oscillator, bottom-right corner -->
  <g opacity="0.4" stroke-linecap="round">
    <path d="M 968 392 Q 966 460 968 528" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 968 402 l 10 -8 M 968 428 l 10 -8 M 968 454 l 10 -8 M 968 480 l 10 -8 M 968 506 l 10 -8" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 968 458 l -14 0 l 6 -12 l -12 24 l -12 -24 l -12 24 l -12 -24 l -12 24 l -12 -24 l -12 24 l -6 -12 l -14 0" stroke="#bfe3ff" stroke-width="3" fill="none"/>
    <rect x="796" y="432" width="48" height="52" rx="4" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 780 528 Q 878 525 972 528" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 820 424 Q 800 418 782 424" stroke="#ffc4c4" stroke-width="2" stroke-dasharray="2 6" fill="none"/>
    <path d="M 782 424 l 9 -4 m -9 4 l 9 4" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <text x="812" y="466" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#ffd9a0">m</text>
    <text x="892" y="440" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#bfe3ff">k</text>
    <text x="836" y="558" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="17" fill="#c8f0c8">ω = √(k/m)</text>
  </g>

  <!-- projectile parabola along bottom edge -->
  <g opacity="0.34" stroke-linecap="round">
    <path d="M 280 532 Q 390 438 500 438 Q 610 438 720 532" stroke="#c8f0c8" stroke-width="3" stroke-dasharray="1 9" fill="none"/>
    <path d="M 285 528 Q 316 500 348 476" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 348 476 l -10 1 m 10 -1 l -3 10" stroke="#ffd9a0" stroke-width="2" fill="none"/>
    <text x="352" y="466" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="15" fill="#ffd9a0">v₀</text>
    <circle cx="500" cy="438" r="4" stroke="none" fill="#c8f0c8"/>
    <path d="M 500 438 l 34 0 m 0 0 l -9 -5 m 9 5 l -9 5" stroke="#bfe3ff" stroke-width="2" fill="none"/>
  </g>

  <!-- chalk formulas along top and bottom edges -->
  <g opacity="0.42">
    <text x="418" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#ffd9a0">F = ma</text>
    <text x="548" y="42" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#bfe3ff">L = T − V</text>
    <text x="446" y="554" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">p = mv,  E = ½mv²</text>
  </g>
</svg>"""
