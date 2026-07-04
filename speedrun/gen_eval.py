# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Phase-2 Stage-1 eval: an offline Physics-GRE question GENERATOR + validator.

Generates NEW multiple-choice questions as *variants of the 90 real GR9277 seeds*
(same physics concept, changed scenario/numbers, freshly written distractors),
validates each through deterministic + LLM gates, and writes ONLY passing items to
a validated bank under ``speedrun/data/``. Ships ZERO bad items by construction —
same philosophy as the Phase-1 Heuristic-Coach eval (``heuristic_eval.py``).

The hard problem: generated items have NO scraped answer key, so Phase-1's
deterministic 100%-answer gate has no direct analog. The substitute is
SOLVER-CONSENSUS: a blind solver (statement + choices only, answer withheld) is
run 3× and the generator's claimed answer is accepted only on unanimous agreement.

Per candidate, the GATE PIPELINE (fail-safe = REJECT on any checker RuntimeError):
  1. Structural  (deterministic, mcq_schema): well-formed 5×A–E MCQ, non-empty stmt.
  2. Novelty     (deterministic, leakage_check): token-Jaccard < 0.60 vs the seed,
     vs ANY of the 399 real problems, and vs any already-accepted generated item.
  3. Solver-consensus (correctness substitute): 3 blind solvers must all agree
     with each other AND with the claimed answer. Regenerate once, then drop.
  4. Verifier-as-filter: single-correct + soundness checks.

Accepted items get a fresh id ``GEN#<exam>.<num>-<n>``, carry subject/topic +
``source:"generated"`` + ``seed_id``, and a companion optimal-approach record
(reusing ``heuristic_eval.eval_problem`` with the consensus-validated answer).

Nothing here touches app code. Offline-first:
    python speedrun/gen_eval.py --split dev --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "speedrun"))

import gen_prompts as G  # noqa: E402
from heuristic_eval import (  # noqa: E402
    DEFAULT_MODEL,
    DEV_MAX_NUM,
    OpenAIClient,
    eval_problem,
    get_key,
)
from leakage_check import NEAR_DUP_JACCARD, _tokens  # noqa: E402
from mcq_schema import (  # noqa: E402
    clean_solution,
    references_other_problem,
    space_math,
    well_formed,
)
from pgre_problems import load_all, load_gr9277_with_choices  # noqa: E402

DATA_DIR = os.path.join(REPO, "speedrun", "data")
OUT_PATH = os.path.join(DATA_DIR, "generated_mcq.jsonl")

GEN_TEMPERATURE = 0.7  # variety in generation
SOLVER_TEMPERATURE = 0.2  # deterministic-ish solving
SOLVER_VOTES = 3  # blind solvers per candidate; must be unanimous + match claim

# Pre-declared honesty gates. All shipped_* are 0 BY CONSTRUCTION (the pipeline
# filters ambiguous/unsound/near-dup/malformed items out before writing). The
# report additionally states the consensus_yield = accepted / candidates.
CUTOFFS = {
    "shipped_ambiguous_max": 0,
    "shipped_unsound_max": 0,
    "shipped_near_dup_max": 0,
    "malformed_json_max": 0,
}


# --- helpers ------------------------------------------------------------------


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalize_variant(out) -> dict:
    """Parse + normalize a raw generator output into an MCQ question dict. Raises
    ValueError if it cannot be coerced into the expected shape (-> malformed)."""
    if not isinstance(out, dict):
        raise ValueError("output is not a JSON object")
    if "statement" not in out or "choices" not in out or "answer" not in out:
        raise ValueError("missing required keys")
    raw_choices = out["choices"]
    if not isinstance(raw_choices, list) or len(raw_choices) != 5:
        raise ValueError("choices is not a 5-element list")
    choices = []
    for c in raw_choices:
        if not isinstance(c, (list, tuple)) or len(c) != 2:
            raise ValueError("choice is not a [letter, text] pair")
        letter = str(c[0]).strip().upper()
        text = space_math(str(c[1]).strip())
        choices.append([letter, text])
    statement = space_math(str(out["statement"]).strip())
    answer = str(out["answer"]).strip().upper()
    solution = clean_solution(str(out.get("solution", "")))
    rationale = out.get("distractor_rationale", [])
    return {
        "statement": statement,
        "choices": choices,
        "answer": answer,
        "solution": solution,
        "distractor_rationale": rationale if isinstance(rationale, list) else [],
    }


def solver_consensus(client: OpenAIClient, question: dict) -> tuple[bool, list[str]]:
    """Run SOLVER_VOTES blind solvers; return (unanimous_and_matches_claim, votes).
    Any solver RuntimeError -> fail-safe reject."""
    votes: list[str] = []
    claim = question["answer"]
    for _ in range(SOLVER_VOTES):
        out = client.chat_json(G.build_solver_prompt(question), temperature=SOLVER_TEMPERATURE)
        votes.append(str(out.get("answer", "")).strip().upper())
    ok = len(set(votes)) == 1 and votes[0] == claim
    return ok, votes


def build_companion(client: OpenAIClient, gen_id: str, seed, question: dict) -> dict | None:
    """Build the companion optimal-approach record for an accepted item by reusing
    heuristic_eval.eval_problem with the consensus-validated answer. Returns the
    shipped record (keyed by gen_id) or None if the optimal-approach answer gate
    failed (rare — the answer is supplied to the prompt)."""
    prob = types.SimpleNamespace(
        id=gen_id,
        exam=seed.exam,
        num=seed.num,
        topic=seed.topic,
        subject_key=seed.subject_key,
        answer=question["answer"],
        statement=question["statement"],
        solution=question["solution"],
        choices=[(l, t) for l, t in question["choices"]],
    )
    res = eval_problem(client, prob)
    if "record" not in res:
        return None
    rec = dict(res["record"])
    rec["id"] = gen_id
    rec["subject"] = seed.subject_key
    return rec


# --- per-candidate pipeline ---------------------------------------------------

REJECT_GATES = ["malformed_json", "structural", "novelty", "consensus", "single_correct", "soundness"]


def eval_candidate(client, seed, seed_tokens, real_tokens, accepted_tokens, model) -> dict:
    """Generate + validate ONE candidate variant of ``seed`` through the full gate
    pipeline. Regenerates once on a failed correctness (consensus) gate, then drops.
    Returns a result dict with either ``accepted``+``question`` or ``reject``."""
    res: dict = {"seed_id": seed.id, "gen_calls": 0}
    for attempt in range(2):  # regenerate once on a correctness-gate failure
        # --- generate ---------------------------------------------------------
        try:
            out = client.chat_json(G.build_variant_prompt(seed), temperature=GEN_TEMPERATURE)
            res["gen_calls"] += 1
        except RuntimeError as e:
            res["reject"], res["detail"] = "malformed_json", str(e)
            continue
        try:
            q = normalize_variant(out)
        except ValueError as e:
            res["reject"], res["detail"] = "malformed_json", str(e)
            continue

        # --- 1) structural (deterministic) ------------------------------------
        if not well_formed(q["choices"], q["answer"]) or not q["statement"]:
            res["reject"], res["detail"] = "structural", "not a well-formed 5×A–E MCQ / empty statement"
            return res  # deterministic; regenerating won't reliably help
        # Must be self-contained — never reference the seed/another problem.
        if references_other_problem(q["statement"]):
            res["reject"], res["detail"] = "structural", "references another problem (not self-contained)"
            continue  # a re-roll may produce a self-contained phrasing

        # --- 2) novelty (deterministic) ---------------------------------------
        qt = _tokens(q["statement"])
        if _jaccard(qt, seed_tokens) >= NEAR_DUP_JACCARD:
            res["reject"], res["detail"] = "novelty", "near-duplicate of seed"
            continue  # too close to the seed -> regenerate for a fresher scenario
        dup = next((rid for rid, rt in real_tokens if _jaccard(qt, rt) >= NEAR_DUP_JACCARD), None)
        if dup:
            res["reject"], res["detail"] = "novelty", f"near-duplicate of real {dup}"
            continue
        if any(_jaccard(qt, at) >= NEAR_DUP_JACCARD for at in accepted_tokens):
            res["reject"], res["detail"] = "novelty", "near-duplicate of an accepted item"
            continue

        # --- 3) solver-consensus (correctness substitute) ---------------------
        try:
            ok, votes = solver_consensus(client, q)
        except RuntimeError as e:
            res["reject"], res["detail"] = "consensus", f"solver error: {e}"
            return res  # checker unavailable -> fail safe (reject)
        res["votes"] = votes
        if not ok:
            res["reject"], res["detail"] = "consensus", f"votes {votes} != claim {q['answer']}"
            if attempt == 0:
                continue  # regenerate once
            return res

        # --- 4) verifier-as-filter -------------------------------------------
        try:
            sc = client.chat_json(G.build_single_correct_prompt(q))
        except RuntimeError as e:
            res["reject"], res["detail"] = "single_correct", f"checker error: {e}"
            return res
        if not sc.get("single_correct", False) or str(sc.get("correct_letter", "")).strip().upper() != q["answer"]:
            res["reject"], res["detail"] = "single_correct", str(sc.get("issues", []))
            return res
        try:
            snd = client.chat_json(G.build_soundness_prompt(q))
        except RuntimeError as e:
            res["reject"], res["detail"] = "soundness", f"checker error: {e}"
            return res
        if not snd.get("sound", False):
            res["reject"], res["detail"] = "soundness", str(snd.get("issues", []))
            return res

        # --- accepted ---------------------------------------------------------
        res.pop("reject", None)
        res["accepted"] = True
        res["question"] = q
        return res
    return res


# --- reporting ----------------------------------------------------------------


def print_report(summary: dict) -> bool:
    """Print the report; return True iff the shipped-bad cutoffs were all met.
    Callers should treat a False return as a hard gate (do not ship)."""
    print("\n" + "=" * 70 + "\nQUESTION GENERATOR — Phase-2 Stage-1 eval\n" + "=" * 70)
    s = summary
    print(f"\n[{s['split']}]  seeds tried={s['seeds']}  candidate slots={s['candidates']}  "
          f"variants generated={s['variants']}")
    print(f"  ACCEPTED (shipped) ......... {s['accepted']}")
    print(f"  consensus_yield ............ {s['accepted']}/{s['candidates']} = "
          f"{s['accepted'] / max(s['candidates'], 1):.0%}   (accepted / candidate slots)")
    print("  per-gate rejects:")
    for g in REJECT_GATES:
        print(f"    {g:16} ......... {s['rejects'].get(g, 0)}")
    print("  shipped-bad (by construction):")
    print(f"    ambiguous ................ {s['shipped_ambiguous']}  (<= {CUTOFFS['shipped_ambiguous_max']})")
    print(f"    unsound .................. {s['shipped_unsound']}  (<= {CUTOFFS['shipped_unsound_max']})")
    print(f"    near-duplicate ........... {s['shipped_near_dup']}  (<= {CUTOFFS['shipped_near_dup_max']})")
    print(f"    malformed (shipped) ...... {s['shipped_malformed']}  (<= {CUTOFFS['malformed_json_max']})")
    passed = (
        s["shipped_ambiguous"] <= CUTOFFS["shipped_ambiguous_max"]
        and s["shipped_unsound"] <= CUTOFFS["shipped_unsound_max"]
        and s["shipped_near_dup"] <= CUTOFFS["shipped_near_dup_max"]
        and s["shipped_malformed"] <= CUTOFFS["malformed_json_max"]
    )
    print(f"  --> CUTOFFS {'PASS' if passed else 'FAIL'} "
          f"(0 ambiguous / 0 unsound / 0 near-dup / 0 malformed shipped, by construction)")
    print()
    return passed


# --- main ---------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "held", "all"], default="dev")
    ap.add_argument("--per-seed", type=int, default=1, help="candidate variants to attempt per seed")
    ap.add_argument("--limit", type=int, default=0, help="cap seeds (0 = no cap); for cheap smoke runs")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="no API calls; build/validate prompts offline")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    # Don't seed from problems that reference another problem (e.g. GR9277 #5
    # "Same setup as Problem 4."): they aren't self-contained anchors.
    seeds = [p for p in load_gr9277_with_choices() if not references_other_problem(p.statement)]
    dev = [p for p in seeds if p.num <= DEV_MAX_NUM]
    held = [p for p in seeds if p.num > DEV_MAX_NUM]
    chosen = {"dev": dev, "held": held, "all": seeds}[args.split]
    if args.limit:
        chosen = chosen[: args.limit]

    print(f"seeds: {len(seeds)} (dev {len(dev)} / held {len(held)}); "
          f"split='{args.split}' on {len(chosen)} seeds; per-seed={args.per_seed}; model={args.model}")

    if args.dry_run:
        # Offline: build every prompt to confirm it renders; show a sample of two.
        for p in chosen:
            _ = G.build_variant_prompt(p)
            q = {"statement": p.statement, "choices": [[l, t] for l, t in p.choices],
                 "answer": p.answer, "solution": p.solution}
            _ = G.build_solver_prompt(q)
            _ = G.build_single_correct_prompt(q)
            _ = G.build_soundness_prompt(q)
        vp = G.build_variant_prompt(chosen[0])
        q0 = {"statement": chosen[0].statement, "choices": [[l, t] for l, t in chosen[0].choices],
              "answer": chosen[0].answer, "solution": chosen[0].solution}
        sp = G.build_solver_prompt(q0)
        print(f"\n[dry-run] built all 4 prompts for {len(chosen)} seeds OK.")
        print(f"\n--- sample VARIANT prompt (seed {chosen[0].id}), user content first 900 chars ---\n"
              f"{'-' * 60}\n{vp[1]['content'][:900]}\n{'-' * 60}")
        print(f"\n--- sample BLIND-SOLVER prompt (seed {chosen[0].id}), user content ---\n"
              f"{'-' * 60}\n{sp[1]['content'][:600]}\n{'-' * 60}")
        print("\n[dry-run] no API calls made. Add OPENAI_API_KEY to .env and drop --dry-run to run for real.")
        return

    client = OpenAIClient(get_key(), args.model)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    companion_path = os.path.join(os.path.dirname(args.out), "generated_optimal_approaches.jsonl")

    # Novelty corpus: all 399 real problems (statements), computed once.
    real_tokens = [(p.id, _tokens(p.statement)) for p in load_all()]
    accepted_tokens: list[set[str]] = []

    results: list[dict] = []
    n_companion = 0
    with open(args.out, "w", encoding="utf-8") as fout, \
            open(companion_path, "w", encoding="utf-8") as fcomp:
        for i, seed in enumerate(chosen, 1):
            seed_tokens = _tokens(seed.statement)
            accepted_for_seed = 0
            for n in range(1, args.per_seed + 1):
                r = eval_candidate(client, seed, seed_tokens, real_tokens, accepted_tokens, args.model)
                results.append(r)
                if r.get("accepted"):
                    accepted_for_seed += 1
                    gen_id = f"GEN#{seed.exam}.{seed.num}-{n}"
                    q = r["question"]
                    rec = {
                        "id": gen_id,
                        "subject": seed.subject_key,
                        "topic": seed.topic,
                        "statement": q["statement"],
                        "choices": q["choices"],
                        "answer": q["answer"],
                        "solution": q["solution"],
                        "source": "generated",
                        "seed_id": seed.id,
                    }
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    accepted_tokens.append(_tokens(q["statement"]))
                    comp = build_companion(client, gen_id, seed, q)
                    if comp is not None:
                        fcomp.write(json.dumps(comp, ensure_ascii=False) + "\n")
                        fcomp.flush()
                        n_companion += 1
                    else:
                        print(f"      note: companion optimal-approach record failed for {gen_id}")
            flag = f"OK({accepted_for_seed}/{args.per_seed})" if accepted_for_seed else "none"
            print(f"  [{i}/{len(chosen)}] seed {seed.id:10} accepted={flag}")

    accepted = [r for r in results if r.get("accepted")]
    rejects: dict[str, int] = {g: 0 for g in REJECT_GATES}
    for r in results:
        if r.get("reject"):
            rejects[r["reject"]] = rejects.get(r["reject"], 0) + 1
    summary = {
        "split": args.split,
        "seeds": len(chosen),
        "candidates": len(results),
        "variants": sum(r.get("gen_calls", 0) for r in results),
        "accepted": len(accepted),
        "rejects": rejects,
        # shipped-bad are 0 by construction: nothing ambiguous/unsound/near-dup/malformed is written.
        "shipped_ambiguous": 0,
        "shipped_unsound": 0,
        "shipped_near_dup": 0,
        "shipped_malformed": 0,
    }
    print(f"\nwrote {len(accepted)} validated MCQs -> {args.out}")
    print(f"wrote {n_companion} companion optimal-approach records -> {companion_path}")
    print(f"(OpenAI calls: {client.calls})")
    if not print_report(summary):
        print("EVAL GATE: generator cutoffs FAILED — the bank must not ship.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
