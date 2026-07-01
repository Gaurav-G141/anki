# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Electromagnetism board."""

TAGLINE = "∇·E = ρ/ε₀ — and let there be light"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- dipole field lines, top-left corner -->
  <g opacity="0.4" stroke-linecap="round">
    <circle cx="60" cy="90" r="14" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 53 90 L 67 90 M 60 83 L 60 97" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <circle cx="185" cy="90" r="14" stroke="#ffc4c4" stroke-width="3" fill="none"/>
    <path d="M 178 90 L 192 90" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <path d="M 74 83 Q 122 52 171 83" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 75 92 Q 122 96 170 92" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 74 99 Q 122 130 171 99" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 128 67 l -10 -4 M 128 67 l -9 6" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 128 114 l -10 -6 M 128 114 l -9 4" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 58 74 Q 55 52 54 34" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 54 34 l -4 10 M 54 34 l 7 9" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 190 76 Q 200 56 206 38" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <path d="M 194 68 l -1 -11 M 194 68 l 10 -4" stroke="#bfe3ff" stroke-width="2.5" fill="none"/>
    <text x="122" y="150" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#bfe3ff">E</text>
  </g>

  <!-- Gaussian surface around a charge, left edge -->
  <g opacity="0.35" stroke-linecap="round">
    <circle cx="110" cy="325" r="62" stroke="#bfe3ff" stroke-width="2.5" stroke-dasharray="7 9" fill="none"/>
    <circle cx="110" cy="325" r="10" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <path d="M 105 325 L 115 325 M 110 320 L 110 330" stroke="#ffc4c4" stroke-width="2" fill="none"/>
    <path d="M 110 256 Q 111 240 110 226" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 110 226 l -6 10 M 110 226 l 7 9" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 170 293 Q 185 285 198 278" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 198 278 l -12 1 M 198 278 l -4 11" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 52 360 Q 38 368 26 375" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 26 375 l 12 -1 M 26 375 l 4 -11" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 138 383 Q 148 397 157 410" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 157 410 l -2 -12 M 157 410 l -11 -3" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <text x="108" y="440" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#bfe3ff">∮E·dA = q/ε₀</text>
  </g>

  <!-- bar magnet with looping B-field, top-right corner -->
  <g opacity="0.38" stroke-linecap="round">
    <rect x="830" y="122" width="120" height="44" rx="4" stroke="#f0ead6" stroke-width="3" fill="none"/>
    <path d="M 890 123 Q 891 144 890 165" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <text x="858" y="153" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#ffc4c4">N</text>
    <text x="922" y="153" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="24" fill="#bfe3ff">S</text>
    <path d="M 838 118 Q 890 42 944 118" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 832 114 Q 890 14 948 114" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 838 170 Q 890 246 944 170" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 896 80 l -11 -3 M 896 80 l -3 -11" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 896 208 l -11 3 M 896 208 l -3 11" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <text x="890" y="42" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#c8f0c8">B</text>
  </g>

  <!-- solenoid cross-section (dots out, crosses in), right edge -->
  <g opacity="0.32" stroke-linecap="round">
    <circle cx="830" cy="315" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="870" cy="315" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="910" cy="315" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="950" cy="315" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="830" cy="315" r="2" stroke="none" fill="#f0ead6"/>
    <circle cx="870" cy="315" r="2" stroke="none" fill="#f0ead6"/>
    <circle cx="910" cy="315" r="2" stroke="none" fill="#f0ead6"/>
    <circle cx="950" cy="315" r="2" stroke="none" fill="#f0ead6"/>
    <circle cx="830" cy="392" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="870" cy="392" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="910" cy="392" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <circle cx="950" cy="392" r="9" stroke="#f0ead6" stroke-width="2.5" fill="none"/>
    <path d="M 825 387 L 835 397 M 835 387 L 825 397" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 865 387 L 875 397 M 875 387 L 865 397" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 905 387 L 915 397 M 915 387 L 905 397" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 945 387 L 955 397 M 955 387 L 945 397" stroke="#f0ead6" stroke-width="2" fill="none"/>
    <path d="M 812 354 Q 884 351 956 354" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
    <path d="M 956 354 l -11 -5 M 956 354 l -10 6" stroke="#c8f0c8" stroke-width="2.5" fill="none"/>
  </g>

  <!-- circuit loop: battery, resistor, capacitor, inductor — bottom band -->
  <g opacity="0.42" stroke-linecap="round">
    <path d="M 80 452 Q 145 448 210 450" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 210 450 l 10 -14 l 16 26 l 16 -26 l 16 26 l 16 -26 l 16 26 l 10 -12" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 310 450 Q 375 447 438 450" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 446 428 Q 447 450 446 472" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 464 428 Q 463 450 464 472" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 472 450 Q 530 453 588 450" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 588 450 a 15 18 0 0 1 30 0 a 15 18 0 0 1 30 0 a 15 18 0 0 1 30 0 a 15 18 0 0 1 30 0" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 708 450 Q 815 447 920 450" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 920 450 Q 923 492 920 534" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 920 534 Q 500 539 80 534" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 80 452 Q 79 472 80 493" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 60 495 Q 80 493 100 495" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <path d="M 70 507 Q 80 506 90 507" stroke="#ffd9a0" stroke-width="4" fill="none"/>
    <path d="M 80 508 Q 81 521 80 534" stroke="#ffd9a0" stroke-width="3" fill="none"/>
    <text x="46" y="494" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">+</text>
    <text x="48" y="518" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">−</text>
    <path d="M 348 432 Q 364 429 380 432" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <path d="M 380 432 l -10 -5 M 380 432 l -9 6" stroke="#ffc4c4" stroke-width="2.5" fill="none"/>
    <text x="392" y="438" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="20" fill="#ffc4c4">I</text>
    <text x="258" y="428" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">R</text>
    <text x="455" y="500" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">C</text>
    <text x="648" y="424" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#ffd9a0">L</text>
    <text x="640" y="512" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#ffd9a0">V = IR</text>
  </g>

  <!-- Lorentz force formula, top strip -->
  <g opacity="0.35">
    <text x="600" y="40" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#ffc4c4">F = qE + qv×B</text>
  </g>
</svg>"""
