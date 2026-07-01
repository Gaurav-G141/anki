# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Chalk drawing for the Quantum Mechanics board."""

TAGLINE = "iħ ∂ψ/∂t = Ĥψ"

SVG = """<svg viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- top-left: blackbody radiation spectrum -->
  <g opacity="0.4" stroke-linecap="round" fill="none">
    <path d="M62,68 Q60,155 63,248" stroke="#f0ead6" stroke-width="3"/>
    <path d="M62,248 Q135,250 212,247" stroke="#f0ead6" stroke-width="3"/>
    <path d="M62,68 l-5,9 M62,68 l6,9" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M212,247 l-9,-5 M212,247 l-9,6" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M67,245 Q78,215 88,150 Q94,110 100,112 Q112,120 130,168 Q160,222 205,232" stroke="#bfe3ff" stroke-width="3"/>
    <path d="M68,246 Q84,228 100,182 Q112,150 120,152 Q132,158 150,196 Q175,232 205,237" stroke="#ffd9a0" stroke-width="3"/>
    <path d="M70,247 Q92,236 116,208 Q130,192 140,193 Q154,197 172,220 Q188,236 205,241" stroke="#ffc4c4" stroke-width="3"/>
    <path d="M205,226 Q150,208 110,155 Q88,120 76,66" stroke="#f0ead6" stroke-width="2.5" stroke-dasharray="7 8"/>
    <text x="52" y="90" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">I</text>
    <text x="200" y="268" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="18" fill="#f0ead6">λ</text>
    <text x="72" y="300" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#bfe3ff">T₃ &gt; T₂ &gt; T₁</text>
    <text x="120" y="98" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#f0ead6">classical</text>
  </g>

  <!-- bottom-left: infinite square well with standing waves -->
  <g opacity="0.38" stroke-linecap="round" fill="none">
    <path d="M62,338 Q60,430 63,522" stroke="#f0ead6" stroke-width="3.5"/>
    <path d="M188,340 Q191,430 189,521" stroke="#f0ead6" stroke-width="3.5"/>
    <path d="M63,522 Q125,524 189,521" stroke="#f0ead6" stroke-width="3.5"/>
    <path d="M66,498 Q125,499 186,497" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M66,456 Q125,458 186,455" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M66,410 Q125,412 186,409" stroke="#f0ead6" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M66,498 Q126,462 186,497" stroke="#ffd9a0" stroke-width="2.5"/>
    <path d="M66,456 Q96,428 126,456 Q156,484 186,455" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M66,410 Q86,388 106,410 Q126,432 146,410 Q166,388 186,409" stroke="#ffc4c4" stroke-width="2.5"/>
    <text x="196" y="503" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#ffd9a0">n=1</text>
    <text x="196" y="461" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#bfe3ff">n=2</text>
    <text x="196" y="415" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#ffc4c4">n=3</text>
    <text x="98" y="358" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#f0ead6">ψₙ(x)</text>
  </g>

  <!-- top-right: harmonic oscillator potential with energy rungs -->
  <g opacity="0.38" stroke-linecap="round" fill="none">
    <path d="M802,62 Q830,178 878,228 Q884,233 890,228 Q936,176 962,64" stroke="#f0ead6" stroke-width="3"/>
    <path d="M849,201 Q884,203 918,200" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M837,171 Q884,173 930,170" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M828,141 Q884,143 940,140" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M820,111 Q884,113 948,110" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="M813,81 Q884,83 955,80" stroke="#ffd9a0" stroke-width="2" stroke-dasharray="6 7"/>
    <text x="792" y="262" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="16" fill="#c8f0c8">Eₙ = (n+½)ħω</text>
    <text x="924" y="207" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="13" fill="#ffd9a0">E₀</text>
  </g>

  <!-- bottom-right: quantum tunneling through a barrier -->
  <g opacity="0.4" stroke-linecap="round" fill="none">
    <path d="M782,470 Q875,472 968,469" stroke="#f0ead6" stroke-width="2.5"/>
    <path d="M868,470 Q866,432 869,396 Q886,393 904,396 Q906,432 905,470" stroke="#f0ead6" stroke-width="3"/>
    <path d="M784,444 Q794,426 804,444 Q814,462 824,444 Q834,426 844,444 Q854,462 864,444" stroke="#bfe3ff" stroke-width="2.5"/>
    <path d="M869,432 Q880,442 903,449" stroke="#ffc4c4" stroke-width="2.5"/>
    <path d="M907,450 Q913,443 919,450 Q925,457 931,450 Q937,443 943,450 Q949,457 955,450 Q961,443 966,450" stroke="#c8f0c8" stroke-width="2.5"/>
    <text x="812" y="418" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#bfe3ff">ψ</text>
    <text x="874" y="384" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#ffc4c4">e⁻ᵏˣ</text>
    <text x="918" y="496" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="14" fill="#c8f0c8">tunneling</text>
  </g>

  <!-- formulas along the top and bottom edges -->
  <g opacity="0.35">
    <text x="500" y="38" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#f0ead6">−ħ²/2m ∇²ψ + Vψ = Eψ</text>
    <text x="500" y="512" text-anchor="middle" font-family="'Chalkboard SE', 'Segoe Print', 'Comic Sans MS', cursive" font-size="22" fill="#ffd9a0">Δx · Δp ≥ ħ/2</text>
  </g>
</svg>"""
