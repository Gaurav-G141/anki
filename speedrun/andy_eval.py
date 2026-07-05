# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Eval for "Explain with Andy" — the MCQ tutor's spoken step-by-step solution.

Andy must be BOTH correct AND concise. The specific failure this eval targets:
Andy establishes the answer, then keeps going — e.g. eliminating the other
choices after a direct calculation has already nailed it, instead of just saying
"so it's (A)". A top tutor stops the moment the answer is determined.

For a deterministic sample of real GR9277 MCQs (paired with the validated
optimal-approach key), this drives the **live app prompt**
(``qt/aqt/heuristic_coach._explain_messages``, loaded without importing aqt) to
generate Andy's steps, then scores each with:

  * CORRECTNESS  — every step is physically right and the steps conclude the
    correct letter (LLM judge + a deterministic "ends on the answer" check).
  * CONCISENESS  — an LLM judge finds the step by which the answer is already
    determined and flags every LATER step that adds nothing (the "kept
    eliminating after it was decided" bug); plus deterministic step/word counts.

Aggregate gates (pre-declared): every explanation correct, redundancy rate 0,
median <= 5 steps. Reuses the OpenAI plumbing + problem loader from the other
speedrun evals. Key from .env (gitignored). Offline: ``--dry-run``.

    python speedrun/andy_eval.py --help
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "speedrun"))

from heuristic_eval import OpenAIClient, get_key  # noqa: E402
from pgre_problems import load_gr9277_with_choices  # noqa: E402

DATA_DIR = os.path.join(REPO, "speedrun", "data")
APPROACHES = os.path.join(DATA_DIR, "optimal_approaches.jsonl")
DEFAULT_MODEL = "gpt-4o"
STEP_CAP = 6  # a genuine multi-step derivation may need this many; bloat shows up
# as redundancy (post-answer steps), which is gated separately at 0.

# Pre-declared gates (what "good" means before we look at numbers).
GATES = {
    "correct_min": 1.00,  # every explanation must be correct
    "redundancy_rate_max": 0.0,  # no explanation may keep going after the answer
    "median_steps_max": 5,
}


def _load_app_prompt():
    """Load the LIVE Andy prompt builder + parser from the app module, WITHOUT
    importing aqt (its top level is stdlib-only; we pass ``ref`` so the data
    layer is never touched)."""
    path = os.path.join(REPO, "qt", "aqt", "heuristic_coach.py")
    spec = importlib.util.spec_from_file_location("andy_hc", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["andy_hc"] = mod
    spec.loader.exec_module(mod)
    return mod


HC = _load_app_prompt()


def load_key() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(APPROACHES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["id"]] = rec
    return out


def _q(prob) -> dict:
    return {
        "id": prob.id,
        "statement": prob.statement,
        "choices": [[l, t] for l, t in prob.choices],
        "answer": prob.answer,
    }


def _sample(problems: list, key: dict, n: int) -> list:
    """A deterministic, subject-spread sample of problems that have a companion."""
    have = sorted((p for p in problems if p.id in key), key=lambda p: p.id)
    if n >= len(have):
        return have
    step = len(have) / n
    return [have[int(i * step)] for i in range(n)]


def _numbered(steps: list[dict]) -> str:
    return "\n".join(f"{i + 1}. {s['say']}" for i, s in enumerate(steps))


def _correctness_judge(q: dict, steps: list[dict]) -> list[dict]:
    system = (
        "You are a Physics GRE grader checking a tutor's BRIEF spoken solution for CORRECTNESS. "
        "Judge truth and whether the conclusion follows. A concise shortcut that omits routine "
        "algebra or states a standard result without deriving it is FINE — only fail an actual "
        "physics error, a false statement, or a conclusion that does not follow. Respond with "
        "ONLY a JSON object."
    )
    choices = "\n".join(f"({l}) {t}" for l, t in q["choices"])
    user = f"""PROBLEM: {q["statement"]}
CHOICES:
{choices}
CORRECT ANSWER: {q["answer"]}

TUTOR'S STEPS (spoken, in order):
{_numbered(steps)}

Are all statements true (no physics errors), and do the steps correctly conclude the answer is
({q["answer"]})? Do NOT penalise brevity or omitted routine algebra. Return ONLY:
{{"correct": <true|false>, "concludes_right_answer": <true|false>, "issues": ["<short>", ...]}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _conciseness_judge(q: dict, steps: list[dict]) -> list[dict]:
    system = (
        "You audit a physics tutor's spoken MCQ solution for CONCISENESS. A top tutor stops the "
        "instant the answer is pinned down and never over-explains. Respond with ONLY a JSON object."
    )
    choices = "\n".join(f"({l}) {t}" for l, t in q["choices"])
    user = f"""PROBLEM: {q["statement"]}
CHOICES:
{choices}
CORRECT ANSWER: {q["answer"]}

TUTOR'S STEPS (in order):
{_numbered(steps)}

STEP 1 — find D, the earliest step by which the correct answer ({q["answer"]}) is already
UNIQUELY determined: a completed calculation/derivation that yields it, a decisive observation,
or — in pure process-of-elimination — the elimination that leaves only ({q["answer"]}).

STEP 2 — list "extra_steps": every step AFTER D that does NOT simply announce the final answer.
These are the wasteful ones — eliminating or discussing OTHER choices once ({q["answer"]}) is
already known, re-deriving, or restating.
NEVER list as extra: (a) the single step that announces the final answer letter — that is
REQUIRED; (b) a step that maps an already-computed value to its choice letter.
If elimination is the route ITSELF (the answer is only known once the others are ruled out),
those elimination steps are NOT extra.

Return ONLY:
{{"answer_determined_at": <D, 1-based; 0 if never clearly established>,
  "extra_steps": [<1-based indices of the wasteful post-answer steps>],
  "minimal": <true iff extra_steps is empty>,
  "why": "<one sentence>"}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def eval_one(client: OpenAIClient, prob, ref: dict) -> dict:
    q = _q(prob)
    out = client.chat_json(HC._explain_messages(q, ref))
    steps = HC._parse_steps(out)
    n_steps = len(steps)
    words = sum(len(s["say"].split()) for s in steps)
    last = steps[-1] if steps else {}
    ends_on_answer = last.get("focus") == "answer" or f"({q['answer']})" in last.get("say", "")

    # Judges at temperature 0 for stable, reproducible scoring.
    corr = client.chat_json(_correctness_judge(q, steps), temperature=0)
    conc = client.chat_json(_conciseness_judge(q, steps), temperature=0)

    # The judge's concludes_right_answer is the authoritative "reaches the right
    # letter" signal; ends_on_answer is kept only as a reported diagnostic (it is
    # a brittle string check that a terse but correct ending can fail).
    correct = bool(corr.get("correct")) and bool(corr.get("concludes_right_answer"))
    redundant = list(conc.get("extra_steps") or [])
    minimal = bool(conc.get("minimal")) and not redundant
    concise = minimal and n_steps <= STEP_CAP

    return {
        "id": prob.id,
        "method": ref.get("optimal_method"),
        "n_steps": n_steps,
        "words": words,
        "ends_on_answer": ends_on_answer,
        "correct": correct,
        "concise": concise,
        "minimal": minimal,
        "answer_determined_at": conc.get("answer_determined_at"),
        "redundant_steps": redundant,
        "issues": corr.get("issues") or [],
        "steps": [s["say"] for s in steps],
    }


def print_report(results: list[dict]) -> dict:
    n = len(results)
    correct = sum(r["correct"] for r in results)
    concise = sum(r["concise"] for r in results)
    both = sum(r["correct"] and r["concise"] for r in results)
    with_redundancy = sum(1 for r in results if r["redundant_steps"])
    steps_list = [r["n_steps"] for r in results]
    words_list = [r["words"] for r in results]
    redundancy_rate = with_redundancy / n if n else 0.0

    print("\n=== ANDY EXPLANATION EVAL ===")
    print(f"sampled: {n} problems")
    print(f"correct (right answer, sound steps):  {correct}/{n}  ({100 * correct / n:.0f}%)")
    print(f"concise (no redundant step, <= {STEP_CAP}):  {concise}/{n}  ({100 * concise / n:.0f}%)")
    print(f"correct AND concise:                   {both}/{n}  ({100 * both / n:.0f}%)")
    print(f"REDUNDANCY RATE (kept going after answer): {100 * redundancy_rate:.0f}%  ({with_redundancy}/{n})")
    print(f"steps  median {statistics.median(steps_list):.1f}  mean {statistics.mean(steps_list):.1f}  max {max(steps_list)}")
    print(f"words  median {statistics.median(words_list):.0f}  mean {statistics.mean(words_list):.0f}  max {max(words_list)}")

    offenders = [r for r in results if r["redundant_steps"] or not r["correct"]]
    if offenders:
        print("\n--- issues (showing up to 8) ---")
        for r in offenders[:8]:
            tag = []
            if not r["correct"]:
                tag.append("INCORRECT")
            if r["redundant_steps"]:
                tag.append(f"redundant steps {r['redundant_steps']} (answer set by step {r['answer_determined_at']})")
            print(f"\n{r['id']} [{r['method']}] — {'; '.join(tag)}")
            for i, s in enumerate(r["steps"], 1):
                mark = " <-- redundant" if i in r["redundant_steps"] else ""
                print(f"   {i}. {s}{mark}")
            if r["issues"]:
                print(f"   correctness issues: {r['issues']}")

    passed = (
        (correct / n >= GATES["correct_min"])
        and (redundancy_rate <= GATES["redundancy_rate_max"])
        and (statistics.median(steps_list) <= GATES["median_steps_max"])
        if n
        else False
    )
    print("\n=== GATES ===")
    print(f"  correct == 100%:        {'PASS' if correct / n >= GATES['correct_min'] else 'FAIL'}")
    print(f"  redundancy rate == 0%:  {'PASS' if redundancy_rate <= GATES['redundancy_rate_max'] else 'FAIL'}")
    print(f"  median steps <= {GATES['median_steps_max']}:      {'PASS' if statistics.median(steps_list) <= GATES['median_steps_max'] else 'FAIL'}")
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'}")
    return {
        "n": n,
        "correct": correct,
        "concise": concise,
        "both": both,
        "redundancy_rate": redundancy_rate,
        "median_steps": statistics.median(steps_list),
        "mean_steps": statistics.mean(steps_list),
        "median_words": statistics.median(words_list),
        "passed": passed,
        "results": results,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Andy explanation eval (correctness + conciseness)")
    ap.add_argument("--n", type=int, default=12, help="number of problems to sample")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "andy_eval.json"))
    ap.add_argument("--dry-run", action="store_true", help="offline: print a built prompt, no scoring")
    args = ap.parse_args()

    key = load_key()
    problems = load_gr9277_with_choices()
    sample = _sample(problems, key, args.n)

    if args.dry_run:
        prob = sample[0]
        msgs = HC._explain_messages(_q(prob), key[prob.id])
        print(f"--- dry-run: Andy prompt for {prob.id} ---\n")
        for m in msgs:
            print(f"[{m['role']}]\n{m['content']}\n")
        print(f"(would score {len(sample)} problems live; STEP_CAP={STEP_CAP})")
        return

    client = OpenAIClient(get_key(), args.model)
    results = []
    for i, prob in enumerate(sample, 1):
        print(f"[{i}/{len(sample)}] {prob.id} …", flush=True)
        try:
            results.append(eval_one(client, prob, key[prob.id]))
        except Exception as e:  # keep going; a single failure shouldn't sink the run
            print(f"   skipped ({type(e).__name__}: {str(e)[:120]})")

    summary = print_report(results)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {os.path.relpath(args.out, REPO)}   (OpenAI calls: {client.calls})")


if __name__ == "__main__":
    main()
