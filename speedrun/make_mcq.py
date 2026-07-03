# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Generate the bundled MCQ question set from the released GR9277 exam.

Parses ``physics-gre-solutions/GR9277.md`` (via ``pgre_problems``) into the clean
``qt/aqt/data/pgre_mcq.json`` the desktop + iOS Practice-MCQs screens read, then
copies it to the iOS app resources. Cleaning applied here (so both platforms get
it):

* strip the trailing ``---`` block separator (and whitespace) that leaks into
  every scraped solution;
* space-normalise inline ``$…$`` math so source concatenations like ``$x$is``
  render as ``x is`` rather than a fused "xis";
* keep only well-formed, gradeable items: exactly five A–E choices, the answer
  among them, and no degenerate choice (a scraper artifact like ``/`` from
  malformed ``(A)/(B)`` groupings — e.g. GR9277 #83, #93).

Run: ``python speedrun/make_mcq.py`` (pure/offline).
"""

from __future__ import annotations

import json
import os
import shutil

import pgre_problems as pp
from mcq_schema import (
    clean_solution,
    difficulty,
    references_other_problem,
    space_math,
    well_formed,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QT_DEST = os.path.join(REPO, "qt", "aqt", "data", "pgre_mcq.json")
IOS_DEST = os.path.join(REPO, "mobile", "SpeedrunApp", "Resources", "pgre_mcq.json")
# The Stage-1 optimal-approach key (AI coach reference + AI-off fallback). Built
# by heuristic_eval.py + bundled to qt; mirror it to iOS so both platforms grade
# against the same validated key.
QT_KEY = os.path.join(REPO, "qt", "aqt", "data", "pgre_optimal_approaches.jsonl")
IOS_KEY = os.path.join(REPO, "mobile", "SpeedrunApp", "Resources", "optimal_approaches.jsonl")


def build() -> list[dict]:
    out = []
    for p in pp.load_gr9277_with_choices():
        if not well_formed(p.choices, p.answer):
            continue
        choices = [[letter, text.strip()] for letter, text in p.choices]
        statement = space_math(p.statement.strip())
        if not statement:
            continue
        solution = clean_solution(p.solution)
        # Drop problems that reference another problem (e.g. GR9277 #5 "Same setup
        # as Problem 4."): they aren't self-contained, so they're ungradeable when
        # shown individually/shuffled in the quiz.
        if references_other_problem(statement):
            continue
        out.append(
            {
                "id": p.id,
                "subject": p.subject_key,
                "topic": p.topic,
                "statement": statement,
                "choices": choices,
                "answer": p.answer,
                "solution": solution,
                # 1–5 difficulty for the quiz's adaptive (ZPD) question selector.
                "difficulty": difficulty(statement, solution, choices),
            }
        )
    return out


def _stamp_generated() -> None:
    """Add/refresh the ``difficulty`` field on the AI-generated bank (produced by a
    separate pipeline) and mirror it to iOS, so generated items join the adaptive
    (ZPD) pool with the same difficulty proxy as the real questions."""
    gen_qt = os.path.join(REPO, "qt", "aqt", "data", "pgre_mcq_generated.json")
    gen_ios = os.path.join(REPO, "mobile", "SpeedrunApp", "Resources", "pgre_mcq_generated.json")
    if not os.path.exists(gen_qt):
        return
    with open(gen_qt, encoding="utf-8") as f:
        payload = json.load(f)
    qs = payload.get("questions", payload if isinstance(payload, list) else [])
    for q in qs:
        q["difficulty"] = difficulty(q.get("statement", ""), q.get("solution", ""), q.get("choices"))
    with open(gen_qt, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    shutil.copyfile(gen_qt, gen_ios)
    print(f"stamped difficulty on {len(qs)} generated MCQs → {gen_qt} + iOS")


def main() -> None:
    questions = build()
    payload = {"exam": "GR9277", "source": "grephysics.net", "questions": questions}
    with open(QT_DEST, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    shutil.copyfile(QT_DEST, IOS_DEST)
    print(f"wrote {len(questions)} MCQs to {QT_DEST}")
    print(f"copied to {IOS_DEST}")

    # Keep the iOS optimal-approach key byte-identical to the desktop's.
    if os.path.exists(QT_KEY):
        shutil.copyfile(QT_KEY, IOS_KEY)
        print(f"synced optimal-approach key → {IOS_KEY}")
    else:
        print(f"note: {QT_KEY} not found; skipped key sync (run heuristic_eval.py first)")

    _stamp_generated()


if __name__ == "__main__":
    main()
