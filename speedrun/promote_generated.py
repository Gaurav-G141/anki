# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Promote the validated Phase-2 generated bank into bundled app resources.

Reads the offline eval output (``speedrun/data/generated_{mcq,optimal_approaches}.jsonl``),
repairs any JSON-mangled LaTeX (see ``mcq_schema.repair_latex``), and writes the
bundled, git-shippable files that BOTH apps load:

  desktop:  qt/aqt/data/pgre_mcq_generated.json
            qt/aqt/data/pgre_optimal_approaches_generated.jsonl   (pgre_* glob ships both)
  iOS:      mobile/SpeedrunApp/Resources/pgre_mcq_generated.json
            mobile/SpeedrunApp/Resources/optimal_approaches_generated.jsonl

The generated MCQ file uses the SAME shape as ``pgre_mcq.json`` (``{exam, source,
questions:[…]}``) so an app loader can just concatenate it with the real bank; each
question keeps ``source:"generated"`` + ``seed_id`` so the UI can badge it. Idempotent
— safe to re-run after another ``gen_eval.py`` pass. Pure/offline, no API key.

    out/pyenv/bin/python speedrun/promote_generated.py
"""

from __future__ import annotations

import json
import os
import shutil

from mcq_schema import repair_latex

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_MCQ = os.path.join(REPO, "speedrun", "data", "generated_mcq.jsonl")
SRC_COMP = os.path.join(REPO, "speedrun", "data", "generated_optimal_approaches.jsonl")

QT_DATA = os.path.join(REPO, "qt", "aqt", "data")
IOS_RES = os.path.join(REPO, "mobile", "SpeedrunApp", "Resources")

QT_MCQ = os.path.join(QT_DATA, "pgre_mcq_generated.json")
QT_COMP = os.path.join(QT_DATA, "pgre_optimal_approaches_generated.jsonl")
IOS_MCQ = os.path.join(IOS_RES, "pgre_mcq_generated.json")
IOS_COMP = os.path.join(IOS_RES, "optimal_approaches_generated.jsonl")


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _fix_mcq(q: dict) -> dict:
    return {
        "id": q["id"],
        "subject": q.get("subject", ""),
        "topic": q.get("topic", ""),
        "statement": repair_latex(q["statement"]),
        "choices": [[l, repair_latex(t)] for l, t in q["choices"]],
        "answer": q["answer"],
        "solution": repair_latex(q.get("solution", "")),
        "source": q.get("source", "generated"),
        "seed_id": q.get("seed_id", ""),
    }


def _fix_comp(r: dict) -> dict:
    r = dict(r)
    r["expert_reasoning"] = repair_latex(r.get("expert_reasoning", ""))
    r["student_explanation"] = repair_latex(r.get("student_explanation", ""))
    r["eliminations"] = [
        {"choice": e.get("choice", ""), "reason": repair_latex(e.get("reason", ""))}
        for e in r.get("eliminations", [])
    ]
    return r


def main() -> None:
    mcqs = [_fix_mcq(q) for q in _read_jsonl(SRC_MCQ)]
    # Provenance gate: every shipped generated item must trace to a real seed
    # (non-empty seed_id) and carry a source — never ship an unsourced item.
    _before = len(mcqs)
    mcqs = [q for q in mcqs if q.get("seed_id") and q.get("source")]
    if len(mcqs) < _before:
        print(f"provenance gate: dropped {_before - len(mcqs)} generated item(s) missing seed_id/source")
    comps = [_fix_comp(r) for r in _read_jsonl(SRC_COMP)]
    if not mcqs:
        raise SystemExit(f"no generated MCQs at {SRC_MCQ}; run gen_eval.py first")

    # DETERMINISTIC ANSWER PIN: the correct answer is the (consensus-validated)
    # MCQ ``answer`` field — the single source of truth the apps display. Force
    # each companion's ``final_answer`` to it so the AI-authored "fastest approach"
    # / coach reference can never state a different letter than the graded answer.
    answer_by_id = {q["id"]: q["answer"] for q in mcqs}
    dropped = 0
    for r in comps:
        pinned = answer_by_id.get(r["id"])
        if pinned and r.get("final_answer", "").upper() != pinned.upper():
            dropped += 1
        if pinned:
            r["final_answer"] = pinned
    if dropped:
        print(f"pinned {dropped} companion answer(s) to the validated MCQ answer")

    # Re-write the (repaired) source artifacts so they stay clean going forward.
    with open(SRC_MCQ, "w", encoding="utf-8") as f:
        for q in mcqs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(SRC_COMP, "w", encoding="utf-8") as f:
        for r in comps:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    payload = {"exam": "GENERATED", "source": "ai-generated (Phase 2)", "questions": mcqs}
    with open(QT_MCQ, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open(QT_COMP, "w", encoding="utf-8") as f:
        for r in comps:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    os.makedirs(IOS_RES, exist_ok=True)
    shutil.copyfile(QT_MCQ, IOS_MCQ)
    shutil.copyfile(QT_COMP, IOS_COMP)

    print(f"promoted {len(mcqs)} generated MCQs + {len(comps)} companion records")
    for p in (QT_MCQ, QT_COMP, IOS_MCQ, IOS_COMP):
        print(f"  wrote {os.path.relpath(p, REPO)}")


if __name__ == "__main__":
    main()
