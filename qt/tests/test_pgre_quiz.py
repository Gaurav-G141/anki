# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the PGRE Performance MCQ quiz core (GUI-free).

Exercise the bundled question data and ``QuizSession`` grading/accuracy against
the in-repo ``qt/aqt/data/pgre_mcq.json`` — no running Qt app needed.
"""

from __future__ import annotations

import os
import re

from aqt import heuristic_coach
from aqt.pgre_quiz import QuizSession, load_questions, select_variants, to_mathjax

DATA = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "aqt", "data", "pgre_mcq.json")
)


def _questions():
    return load_questions(DATA)


def _generated(qs):
    return [q for q in qs if str(q.get("id", "")).startswith("GEN#")]


def test_bundled_questions_are_wellformed_and_gradeable():
    qs = _questions()
    assert len(qs) >= 50, "expected a substantial MCQ set"
    for q in qs:
        assert set(q) >= {"id", "statement", "choices", "answer"}
        letters = {c[0] for c in q["choices"]}
        assert letters == set("ABCDE"), f"{q['id']} choices not A–E: {letters}"
        # Every question is gradeable: the answer key is one of the choices.
        assert q["answer"] in letters, f"{q['id']} answer not among choices"
        assert q["statement"].strip()
        # No degenerate choices (e.g. a stray "/" from a malformed source group).
        for _, text in q["choices"]:
            assert re.search(r"[A-Za-z0-9]", text) or "$" in text, (
                f"{q['id']} degenerate choice {text!r}"
            )
        # The scraped markdown separator must not leak into the solution.
        assert not q["solution"].rstrip().endswith("---"), (
            f"{q['id']} solution has trailing ---"
        )


def test_session_grades_correct_and_incorrect():
    qs = _questions()
    # Deterministic 2-question order.
    s = QuizSession(qs, order=[0, 1])
    q0 = s.current()
    assert q0 is qs[0]
    assert s.submit(qs[0]["answer"]) is True  # correct
    s.advance()
    wrong = next(l for l in "ABCDE" if l != qs[1]["answer"])
    assert s.submit(wrong) is False  # incorrect
    s.advance()
    assert s.done
    assert s.answered == 2
    assert s.correct == 1
    assert s.accuracy == 0.5


def test_double_submit_does_not_inflate_counts():
    qs = _questions()
    s = QuizSession(qs, order=[0])
    assert s.submit(qs[0]["answer"]) is True
    # A second submit on the same question is ignored.
    assert s.submit(qs[0]["answer"]) is None
    assert s.answered == 1
    assert s.correct == 1


def test_advance_requires_an_answer():
    qs = _questions()
    s = QuizSession(qs, order=[0, 1])
    s.advance()  # no answer yet → no-op
    assert s.current() is qs[0]
    assert s.pos == 0


def test_accuracy_zero_when_nothing_answered():
    s = QuizSession(_questions(), order=[0])
    assert s.answered == 0
    assert s.accuracy == 0.0
    assert s.current() is not None
    assert s.done is False


def test_generated_questions_are_in_the_pool():
    qs = _questions()
    gen = _generated(qs)
    assert gen, "expected the AI-generated (GEN#…) bank to be folded into the pool"


def test_generated_questions_are_wellformed():
    # A generated question is gradeable like a real one: 5 A–E choices, and its
    # answer key is one of them.
    for q in _generated(_questions()):
        letters = {c[0] for c in q["choices"]}
        assert letters == set("ABCDE"), f"{q['id']} choices not A–E: {letters}"
        assert len(q["choices"]) == 5, f"{q['id']} does not have exactly 5 choices"
        assert q["answer"] in letters, f"{q['id']} answer not among choices"


def test_generated_questions_have_resolvable_companions():
    # Every generated item resolves to an optimal-approach companion (so the
    # Coach + "Fastest approach" card work for generated questions too).
    gen = _generated(_questions())
    assert gen, "no generated questions to check"
    for q in gen:
        rec = heuristic_coach.optimal_for(q["id"])
        assert rec is not None, f"{q['id']} has no optimal-approach companion"
        assert rec.get("student_explanation", "").strip(), (
            f"{q['id']} companion missing student_explanation"
        )


def test_to_mathjax_converts_dollar_delimiters():
    assert to_mathjax(r"momentum $\hbar k$ here") == r"momentum \(\hbar k\) here"
    assert to_mathjax(r"$$\lambda = 2d$$") == r"\[\lambda = 2d\]"


# --- reworded-variant serving (fluency-illusion fix) ----------------------


def _fixture_with_rewords():
    """A seed + 2 rewordings, a novel generated variant of the same seed, and an
    unrelated question — the shapes select_variants must group correctly."""
    return [
        {"id": "GR9277#1", "answer": "A", "choices": [["A", "a"]], "statement": "seed"},
        {
            "id": "RW#GR9277.1-1",
            "seed_id": "GR9277#1",
            "source": "reworded",
            "answer": "A",
            "choices": [["A", "a"]],
            "statement": "reword one",
        },
        {
            "id": "RW#GR9277.1-2",
            "seed_id": "GR9277#1",
            "source": "reworded",
            "answer": "A",
            "choices": [["A", "a"]],
            "statement": "reword two",
        },
        {
            "id": "GEN#GR9277.1-1",
            "seed_id": "GR9277#1",
            "source": "generated",
            "answer": "B",
            "choices": [["B", "b"]],
            "statement": "novel variant",
        },
        {
            "id": "GR9277#2",
            "answer": "C",
            "choices": [["C", "c"]],
            "statement": "other",
        },
    ]


def test_select_variants_one_reworded_variant_per_seed():
    qs = _fixture_with_rewords()
    sel, rot = select_variants(qs, {})
    ids = [q["id"] for q in sel]
    # One item for the GR9277#1 concept group (seed+rewords), the novel GEN item
    # stays independent, and the unrelated seed passes through.
    assert "GEN#GR9277.1-1" in ids and "GR9277#2" in ids
    seed_group = [i for i in ids if i == "GR9277#1" or i.startswith("RW#GR9277.1")]
    assert len(seed_group) == 1, (
        f"expected exactly one variant of the seed, got {seed_group}"
    )
    # First session serves the original seed (rotation 0 -> members[0]).
    assert seed_group[0] == "GR9277#1"


def test_select_variants_rotates_across_sessions():
    qs = _fixture_with_rewords()
    served = []
    rot: dict[str, int] = {}
    for _ in range(4):
        sel, rot = select_variants(qs, rot)
        served.append(
            next(
                q["id"]
                for q in sel
                if q["id"].startswith(("GR9277#1", "RW#GR9277.1"))
                and q["id"] != "GR9277#2"
            )
        )
    # 3 variants (seed + 2 rewords) cycle: seed, rw-1, rw-2, seed, …
    assert served == ["GR9277#1", "RW#GR9277.1-1", "RW#GR9277.1-2", "GR9277#1"], served


def test_select_variants_noop_without_rewords():
    qs = _questions()  # the shipped bank may or may not carry rewords
    sel, _ = select_variants(qs, {})
    # Every concept appears once; total shrinks only by the number of extra variants.
    keys = {
        (q.get("seed_id") if q.get("source") == "reworded" else q["id"]) for q in qs
    }
    assert len(sel) == len(keys)


def test_reworded_variants_are_wellformed_and_resolvable():
    # Any shipped reworded item must be gradeable (5 A–E choices, answer among them),
    # keep its seed's answer, and resolve an optimal-approach companion. Vacuous (and
    # fine) until the reworded bank is generated + promoted. (Self-containment + the
    # reword similarity band are enforced separately by speedrun/gen_leakage_check.py.)
    qs = _questions()
    by_id = {q["id"]: q for q in qs}
    rewords = [q for q in qs if q.get("source") == "reworded"]
    for q in rewords:
        letters = {c[0] for c in q["choices"]}
        assert letters == set("ABCDE") and len(q["choices"]) == 5, (
            f"{q['id']} not 5 A–E choices"
        )
        assert q["answer"] in letters, f"{q['id']} answer not among choices"
        seed = by_id.get(q.get("seed_id", ""))
        if seed is not None:
            assert q["answer"] == seed["answer"], (
                f"{q['id']} answer differs from its seed"
            )
        rec = heuristic_coach.optimal_for(q["id"])
        assert rec is not None and rec.get("student_explanation", "").strip(), (
            f"{q['id']} has no resolvable optimal-approach companion"
        )
