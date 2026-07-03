# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Shared "well-formed MCQ" validators + normalizers (single source of truth).

Extracted from ``make_mcq.py`` so both the real-problem pipeline and the Phase-2
question generator (``gen_eval.py``) enforce the SAME notion of a gradeable MCQ:

* exactly five A–E choices, the claimed answer among them, and no degenerate
  choice (a scraper/generation artifact with no alphanumerics and no ``$`` math);
* inline ``$…$`` math space-normalised so concatenations like ``$x$is`` render as
  ``x is`` rather than a fused "xis"; and the trailing markdown ``---`` separator
  stripped from scraped solutions.

Pure/offline — no network, no API key.
"""

from __future__ import annotations

import re

_INLINE = re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")

# LaTeX backslash-commands that a model emitted with a SINGLE backslash inside a
# JSON string get silently decoded by JSON into ASCII control characters
# (`\frac` -> FORM-FEED+"rac", `\text` -> TAB+"ext", `\beta` -> BACKSPACE+"eta").
# Repair them back to the intended `\<letter>`. The BS/TAB/VT/FF forms are never
# legitimately present in a physics string, so they're safe to repair anywhere;
# NL/CR are ambiguous (real line breaks in prose) so we only repair those inside
# ``$…$`` / ``$$…$$`` math spans.
_CTRL_SAFE = {"\x08": r"\b", "\x09": r"\t", "\x0b": r"\v", "\x0c": r"\f"}
_CTRL_MATH_ONLY = {"\x0a": r"\n", "\x0d": r"\r"}
_MATH_SPAN = re.compile(r"\$\$.+?\$\$|\$[^\n]+?\$", re.S)


def repair_latex(text: str) -> str:
    """Undo JSON's control-character mangling of single-backslash LaTeX commands."""
    if not text:
        return text
    for ctrl, rep in _CTRL_SAFE.items():
        text = text.replace(ctrl, rep)
    if any(ctrl in text for ctrl in _CTRL_MATH_ONLY):

        def _fix(m: re.Match) -> str:
            seg = m.group(0)
            for ctrl, rep in _CTRL_MATH_ONLY.items():
                seg = seg.replace(ctrl, rep)
            return seg

        text = _MATH_SPAN.sub(_fix, text)
    return text


def space_math(text: str) -> str:
    """Ensure inline ``$…$`` is space-separated from adjacent words, then collapse
    runs of spaces. Leaves display ``$$…$$`` and newlines alone. Also repairs
    JSON-mangled LaTeX (see ``repair_latex``) so ``$\\frac…$`` renders."""
    text = repair_latex(text)
    text = _INLINE.sub(r" $\1$ ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def clean_solution(text: str) -> str:
    text = re.sub(r"\s*-{3,}\s*$", "", text)  # drop trailing markdown separator
    return space_math(text).strip()


def is_degenerate(choice_text: str) -> bool:
    """A choice with neither an alphanumeric nor any math ($) is a bad parse."""
    return not re.search(r"[A-Za-z0-9]", choice_text) and "$" not in choice_text


# A standalone MCQ (shown individually / shuffled) must be self-contained: a
# statement that leans on another problem ("Same setup as Problem 4.") is
# ungradeable on its own. Catches scraped exam cross-references AND any generated
# candidate that references its seed.
_CROSS_REF = re.compile(
    # Statement LEADS with a back-reference to a carried-over object from a prior
    # part of a multi-part problem, e.g. "Same cylinder slows from 80 to 40 rad/s"
    # or "For the same circuit, find the voltage across R_4". Multi-part
    # continuations essentially always open this way, so anchoring on a leading
    # "same" is both robust and low-false-positive (a self-contained "of the same
    # mass" appears mid-sentence, never at the start).
    r"^\s*same\b"
    r"|^\s*(for|in|with|using|on|from|consider|take|assume|now|again)\s+(the\s+)?same\b"
    # Mid-sentence explicit cross-references.
    r"|\b(same (setup|configuration|system|situation|arrangement|circuit|cylinder"
    r"|apparatus|network|capacitor|conductor|particle|gas|rod|beam|wire|loop|coil"
    r"|disk|sphere|block|spring|pendulum) as"
    r"|as in (the )?(previous|preceding|earlier|prior|above) problem"
    r"|as in problem|see problem|refer to problem|from problem"
    r"|(previous|preceding|earlier|prior) problem"
    r"|problem\s+\d+"
    r"|the (anchor|original) (problem|question))\b",
    re.I,
)


def references_other_problem(text: str) -> bool:
    """True if the statement refers to another problem (not self-contained)."""
    return bool(_CROSS_REF.search(text or ""))


# Deterministic difficulty proxy (1 = easiest … 5 = hardest), used by the quiz's
# adaptive "zone of proximal development" selector on both apps. No LLM / no
# per-question labels needed: harder GRE items tend to carry denser math and
# longer stems/solutions. Soft by design — it only has to give the adaptive
# engine a usable spread to climb/descend.
_MATH_TOKENS = re.compile(
    r"\\frac|\\int|\\oint|\\sqrt|\\partial|\\nabla|\\sum|\\prod|\\vec|\\hat|\\dot"
    r"|\\omega|\\psi|\\phi|\\hbar|\\times|\\cdot|\\pi|\\epsilon|\\mu|\\lambda|\\Delta"
    r"|\\alpha|\\beta|\\gamma|\\theta|\\rho|\\sigma|\^|_"
)


def difficulty(statement: str, solution: str = "", choices=None) -> int:
    """A 1–5 difficulty estimate from math density + stem/solution length."""
    stmt = statement or ""
    sol = solution or ""
    math = len(_MATH_TOKENS.findall(stmt + " " + sol))
    score = min(3, math // 4)  # 0–3 from math density
    if len(stmt) > 160:
        score += 1  # long stem
    if len(stmt) > 300:
        score += 1
    if len(sol) > 240:
        score += 1  # deep solution
    return max(1, min(5, 1 + score))


def well_formed(choices, answer) -> bool:
    """True iff ``choices`` is exactly the five A–E options, ``answer`` is one of
    those letters, and no choice is degenerate. ``choices`` may be a list of
    ``(letter, text)`` tuples or ``[letter, text]`` lists. The caller separately
    checks that the statement is non-empty (context-specific)."""
    letters = {letter for letter, _ in choices}
    if len(choices) != 5 or letters != set("ABCDE"):
        return False
    if str(answer).strip().upper() not in letters:
        return False
    if any(is_degenerate(text) for _, text in choices):
        return False
    return True
