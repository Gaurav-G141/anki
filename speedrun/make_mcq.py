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
from mcq_schema import clean_solution, references_other_problem, space_math, well_formed

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
                "solution": clean_solution(p.solution),
            }
        )
    return out


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


if __name__ == "__main__":
    main()
