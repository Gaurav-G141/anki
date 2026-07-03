# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Parse the scraped Physics-GRE problem sets into structured records.

Reads `physics-gre-solutions/GR{8677,9277,9677,0177}.md` (real released ETS
exams, community-scraped from grephysics.net) into `Problem` records that the
Heuristic-Coach eval harness consumes. Pure/offline — no network, no API key.

File format (per README), one block per problem:

    ## Problem N
    **Topic:** <Subject → subtopic>
    **Answer:** <letter, or a value for a few flagged items>

    <statement, possibly multi-line LaTeX>

    Choices: (A) .. (B) .. (C) .. (D) .. (E) ..     # GR9277 only
    **Solution:** <worked solution>
    ---

Only GR9277 lists answer choices inline; the POE / estimation heuristics need
them, so `has_choices` marks the usable-for-choice-work subset.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOLUTIONS_DIR = os.path.join(REPO, "physics-gre-solutions")
EXAMS = ["GR8677", "GR9277", "GR9677", "GR0177"]

# README-documented items to skip or flag.
SKIP = {("GR9677", 90)}  # ETS unscored item — no statement/solution
TYPO_FLAG = {("GR9277", 53), ("GR9277", 55), ("GR9277", 82)}
VALUE_ANSWER_FLAG = {  # answer captured as a value/result, not a clean letter
    ("GR0177", n) for n in (5, 12, 16, 23, 27, 45, 98)
} | {("GR8677", n) for n in (25, 52, 55, 95)}

# Map the top-level of the `Topic:` field to a taxonomy subject key. Best-effort;
# used only for per-subject reporting, not for grading correctness.
_SUBJECT_KEYWORDS = [
    ("special_relativity", ("special relativity", "relativity")),
    ("atomic_physics", ("atomic", "nuclear", "particle")),
    ("quantum_mechanics", ("quantum",)),
    ("thermo_stat_mech", ("thermo", "statistical", "stat mech", "kinetic")),
    ("optics_waves", ("optic", "wave", "acoustic", "interference", "diffraction")),
    ("electromagnetism", ("electro", "magnet", "circuit", "e&m", "em ")),
    ("lab_methods", ("lab", "measurement", "error", "instrument", "data analysis")),
    ("classical_mechanics", ("mechanic", "newton", "lagrang", "orbit", "oscillat", "fluid")),
    ("specialized_topics", ("special", "misc", "math", "astro", "condensed", "solid state")),
]

_CHOICE_RE = re.compile(r"\(([A-E])\)\s*(.*?)(?=\s*\([A-E]\)|$)", re.S)


@dataclass
class Problem:
    exam: str
    num: int
    topic: str  # raw "Subject → subtopic"
    subject_key: str  # mapped taxonomy key (best-effort)
    answer: str  # scraped ground-truth answer (letter, or value for flagged)
    statement: str
    solution: str
    choices: list[tuple[str, str]] = field(default_factory=list)  # [(letter, text)]
    has_choices: bool = False
    answer_is_letter: bool = False
    flags: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.exam}#{self.num}"


def _subject_key(topic: str) -> str:
    t = topic.lower()
    for key, kws in _SUBJECT_KEYWORDS:
        if any(kw in t for kw in kws):
            return key
    return "unknown"


def _parse_choices(line: str) -> list[tuple[str, str]]:
    body = line.split("Choices:", 1)[1] if "Choices:" in line else line
    out = [(letter, text.strip()) for letter, text in _CHOICE_RE.findall(body)]
    return out


def _parse_block(exam: str, num: int, block: str) -> Problem | None:
    if (exam, num) in SKIP:
        return None
    topic_m = re.search(r"^\*\*Topic:\*\*\s*(.+)$", block, re.M)
    ans_m = re.search(r"^\*\*Answer:\*\*\s*(.+)$", block, re.M)
    sol_m = re.search(r"^\*\*Solution:\*\*\s*(.*)$", block, re.M | re.S)
    if not (topic_m and ans_m):
        return None
    topic = topic_m.group(1).strip()
    answer_raw = ans_m.group(1).strip()

    choices_m = re.search(r"^Choices:.*$", block, re.M)
    # statement = text between the Answer line and the Choices/Solution line
    after_answer = block[ans_m.end():]
    cut = len(after_answer)
    for m in (choices_m, sol_m):
        if m:
            idx = block.find(m.group(0), ans_m.end())
            if idx != -1:
                cut = min(cut, idx - ans_m.end())
    statement = after_answer[:cut].strip()

    choices = _parse_choices(choices_m.group(0)) if choices_m else []
    solution = sol_m.group(1).strip() if sol_m else ""

    # A clean letter answer is a single A–E (the flagged value-answers are not).
    answer_is_letter = bool(re.fullmatch(r"[A-E]", answer_raw)) and (exam, num) not in VALUE_ANSWER_FLAG

    flags = []
    if (exam, num) in TYPO_FLAG:
        flags.append("source_typo")
    if (exam, num) in VALUE_ANSWER_FLAG:
        flags.append("value_answer")

    return Problem(
        exam=exam,
        num=num,
        topic=topic,
        subject_key=_subject_key(topic),
        answer=answer_raw,
        statement=statement,
        solution=solution,
        choices=choices,
        has_choices=bool(choices),
        answer_is_letter=answer_is_letter,
        flags=flags,
    )


def parse_exam(exam: str) -> list[Problem]:
    path = os.path.join(SOLUTIONS_DIR, f"{exam}.md")
    text = open(path, encoding="utf-8").read()
    # split into per-problem blocks on the "## Problem N" headers
    parts = re.split(r"^## Problem (\d+)\s*$", text, flags=re.M)
    # parts = [preamble, "1", block1, "2", block2, ...]
    problems = []
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        block = parts[i + 1]
        p = _parse_block(exam, num, block)
        if p:
            problems.append(p)
    return problems


def load_all() -> list[Problem]:
    out = []
    for exam in EXAMS:
        out.extend(parse_exam(exam))
    return out


def load_gr9277_with_choices() -> list[Problem]:
    """The primary set for the full heuristic coach: real problems WITH choices
    and a clean letter answer (excludes source-typo-flagged items)."""
    return [
        p
        for p in parse_exam("GR9277")
        if p.has_choices and p.answer_is_letter and "source_typo" not in p.flags
    ]


if __name__ == "__main__":
    allp = load_all()
    print(f"parsed {len(allp)} problems across {len(EXAMS)} exams")
    for exam in EXAMS:
        ps = [p for p in allp if p.exam == exam]
        wc = sum(p.has_choices for p in ps)
        wl = sum(p.answer_is_letter for p in ps)
        print(f"  {exam}: {len(ps)} problems, {wc} with choices, {wl} clean-letter answers")
    primary = load_gr9277_with_choices()
    print(f"\nprimary set (GR9277 w/ choices + clean letter): {len(primary)} problems")
    ex = primary[0]
    print(f"\n--- sample: {ex.id}  [{ex.subject_key}] answer={ex.answer} ---")
    print("statement:", ex.statement[:160].replace("\n", " "))
    print("choices:", [(l, t[:24]) for l, t in ex.choices])
    print("solution:", ex.solution[:160].replace("\n", " "))
    # subject distribution
    from collections import Counter
    dist = Counter(p.subject_key for p in allp)
    print("\nsubject distribution (all):", dict(dist))
