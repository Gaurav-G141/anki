# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Phase-2b: generate VALIDATED reworded variants of the shipped MCQ bank.

The Speed Recall Brainlift names the "fluency illusion" — students pattern-match the
*card* rather than retrieving the *concept* — as Anki's core weakness. The fix is
**varied surface forms of the same question**: keep the physics, numbers, choices, and
answer identical; reword only the stem. This script pre-generates those rewordings
OFFLINE (so study time stays fast, deterministic, and API-free) and writes them into the
same ``generated_mcq.jsonl`` the app already ships, tagged ``source:"reworded"`` +
``seed_id`` so the apps can rotate one variant per concept across sessions.

Per seed (a real ``pgre_mcq.json`` question), for each of ``--k`` variants:
  1. Reword the stem via ``gen_prompts.build_paraphrase_prompt`` (choices/answer held fixed).
  2. INTEGRITY (reuse ``paraphrase_eval._reword_issues``): 0.15 ≤ Jaccard(orig,reword) < 0.75
     (surface actually changed but same problem), no answer-letter leak, not degenerate,
     and ``mcq_schema.references_other_problem`` False (self-contained). NB: we deliberately
     do NOT apply the 0.60 near-dup NOVELTY gate — a same-physics reword *should* overlap
     its seed; that gate is for *novel* items only (``gen_eval``).
  3. CORRECTNESS (reuse ``gen_eval.solver_consensus``): 3 blind solvers must unanimously
     pick the seed's answer — proves the reword didn't change what's being asked.
  4. VERIFY: single-correct + soundness checks.
The companion optimal-approach is the seed's existing companion re-keyed to the variant id
(physics/method unchanged), so the coach's "Fastest approach" card resolves with no regen.

Idempotent: preserves any ``source:"generated"`` items and other companions; only the
``source:"reworded"`` / ``RW#`` records are rewritten. Merge into the shipped banks with
``promote_generated.py``. Offline-first:  python speedrun/gen_reword_variants.py --dry-run
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
from gen_eval import solver_consensus  # noqa: E402  (reuse the blind-solver consensus)
from heuristic_eval import DEFAULT_MODEL, OpenAIClient, get_key  # noqa: E402
from mcq_schema import clean_solution, references_other_problem, space_math, well_formed  # noqa: E402
from paraphrase_eval import _reword_issues  # noqa: E402  (reuse the reword integrity band)

DATA_DIR = os.path.join(REPO, "speedrun", "data")
REAL_BANK = os.path.join(REPO, "qt", "aqt", "data", "pgre_mcq.json")
GEN_MCQ = os.path.join(DATA_DIR, "generated_mcq.jsonl")
GEN_COMP = os.path.join(DATA_DIR, "generated_optimal_approaches.jsonl")
SEED_COMP = os.path.join(DATA_DIR, "optimal_approaches.jsonl")

DEFAULT_K = 2               # reworded variants per seed
DEFAULT_N = 40             # seeds to reword (0 = all); caps first-cut API cost
REWORD_TEMPERATURE = 0.7   # variety in the reword

REJECT_GATES = ["malformed_json", "integrity", "structural", "consensus", "single_correct", "soundness"]


# --- helpers ------------------------------------------------------------------


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


def _seed_ns(q: dict) -> types.SimpleNamespace:
    """A Problem-like namespace for a real-bank question (build_paraphrase_prompt +
    _reword_issues only need ``.statement``; the rest labels the variant)."""
    exam, _, num = str(q["id"]).partition("#")
    return types.SimpleNamespace(
        id=q["id"], exam=exam or "GR", num=int(num) if num.isdigit() else 0,
        statement=q["statement"], choices=[(l, t) for l, t in q["choices"]],
        answer=str(q["answer"]).strip().upper(), solution=q.get("solution", ""),
        subject_key=q.get("subject", ""), topic=q.get("topic", ""),
        difficulty=q.get("difficulty", 3),
    )


def eval_reword(client: OpenAIClient, seed: types.SimpleNamespace, variant: int) -> dict:
    """Generate + validate ONE reworded variant of ``seed`` through the gate pipeline.
    Regenerates once on a correctness (consensus) failure, then drops."""
    res: dict = {"seed_id": seed.id, "variant": variant, "gen_calls": 0}
    seed_q = {"statement": seed.statement, "choices": [[l, t] for l, t in seed.choices],
              "answer": seed.answer, "solution": seed.solution}
    if not well_formed(seed_q["choices"], seed.answer):
        res["reject"], res["detail"] = "structural", "seed is not a well-formed 5×A–E MCQ"
        return res
    for attempt in range(2):
        # --- reword the stem (choices/answer held fixed) ----------------------
        try:
            out = client.chat_json(G.build_paraphrase_prompt(seed, variant), temperature=REWORD_TEMPERATURE)
            res["gen_calls"] += 1
        except RuntimeError as e:
            res["reject"], res["detail"] = "malformed_json", str(e)
            continue
        stmt = space_math(str(out.get("statement", "")).strip())

        # --- integrity: reword band + answer-leak + self-contained ------------
        issues = _reword_issues(seed, stmt)
        if issues:
            res["reject"], res["detail"] = "integrity", issues
            continue  # re-roll may land inside the band
        if references_other_problem(stmt):
            res["reject"], res["detail"] = "structural", "references another problem (not self-contained)"
            continue

        q = {"statement": stmt, "choices": seed_q["choices"], "answer": seed.answer, "solution": seed.solution}

        # --- correctness: blind-solver consensus == the seed's answer ---------
        try:
            ok, votes = solver_consensus(client, q)
        except RuntimeError as e:
            res["reject"], res["detail"] = "consensus", f"solver error: {e}"
            return res  # checker unavailable -> fail safe
        res["votes"] = votes
        if not ok:
            res["reject"], res["detail"] = "consensus", f"votes {votes} != seed answer {seed.answer}"
            if attempt == 0:
                continue
            return res

        # --- verify: single-correct + soundness -------------------------------
        try:
            sc = client.chat_json(G.build_single_correct_prompt(q))
        except RuntimeError as e:
            res["reject"], res["detail"] = "single_correct", f"checker error: {e}"
            return res
        if not sc.get("single_correct", False) or str(sc.get("correct_letter", "")).strip().upper() != seed.answer:
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

        res.pop("reject", None)
        res["accepted"] = True
        res["statement"] = stmt
        return res
    return res


def _record(seed: types.SimpleNamespace, n: int, stmt: str) -> dict:
    return {
        "id": f"RW#{seed.exam}.{seed.num}-{n}",
        "subject": seed.subject_key, "topic": seed.topic,
        "statement": stmt,
        "choices": [[l, t] for l, t in seed.choices],
        "answer": seed.answer,
        "solution": clean_solution(seed.solution),
        "difficulty": seed.difficulty,
        "source": "reworded",
        "seed_id": seed.id,
    }


def _companion(seed_comps: dict, rw_id: str, seed: types.SimpleNamespace) -> dict | None:
    """Reuse the seed's existing optimal-approach companion, re-keyed to the variant id
    (physics/method are unchanged by a reword). Answer pinned to the seed's answer."""
    base = seed_comps.get(seed.id)
    if not base:
        return None
    comp = dict(base)
    comp["id"] = rw_id
    comp["subject"] = seed.subject_key
    comp["final_answer"] = seed.answer
    return comp


# --- report -------------------------------------------------------------------


def print_report(summary: dict) -> bool:
    print("\n" + "=" * 70 + "\nREWORDED-VARIANT GENERATOR (fluency-illusion fix)\n" + "=" * 70)
    s = summary
    print(f"\n  seeds tried ................ {s['seeds']}")
    print(f"  variant slots (seeds×k) .... {s['candidates']}")
    print(f"  ACCEPTED (shipped) ......... {s['accepted']}")
    print(f"  yield ...................... {s['accepted']}/{max(s['candidates'],1)} = "
          f"{s['accepted']/max(s['candidates'],1):.0%}")
    print("  per-gate rejects:")
    for g in REJECT_GATES:
        print(f"    {g:16} ......... {s['rejects'].get(g, 0)}")
    print(f"  seeds with >=1 variant ..... {s['seeds_covered']}")
    print(f"  companions attached ........ {s['companions']}/{s['accepted']}")
    # Hard signal: if we tried seeds but shipped nothing, something is wrong.
    passed = not (s["seeds"] > 0 and s["accepted"] == 0)
    print(f"  --> {'OK' if passed else 'FAIL (0 accepted from >0 seeds)'}")
    print()
    return passed


# --- main ---------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="seeds to reword (0 = all real-bank questions)")
    ap.add_argument("--k", type=int, default=DEFAULT_K, help="reworded variants per seed")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="no API calls; build/validate prompts offline")
    args = ap.parse_args()

    bank = json.load(open(REAL_BANK, encoding="utf-8"))["questions"]
    seeds = [_seed_ns(q) for q in bank]
    # Don't reword items that reference another problem (not self-contained anchors).
    seeds = [s for s in seeds if not references_other_problem(s.statement)]
    chosen = seeds if args.n <= 0 else seeds[: args.n]
    print(f"real bank: {len(bank)} questions; rewording {len(chosen)} seeds × {args.k} variants; model={args.model}")

    if args.dry_run:
        s0 = chosen[0]
        for s in chosen:
            for v in range(args.k):
                _ = G.build_paraphrase_prompt(s, v)
        sample = G.build_paraphrase_prompt(s0, 0)
        print(f"\n[dry-run] built {len(chosen)*args.k} paraphrase prompts OK.")
        print(f"[dry-run] sample reword prompt (seed {s0.id}), first 700 chars:\n{'-'*60}\n"
              f"{sample[1]['content'][:700]}\n{'-'*60}")
        print("[dry-run] no API calls made. Add OPENAI_API_KEY to .env and drop --dry-run to run for real.")
        return

    client = OpenAIClient(get_key(), args.model)
    seed_comps = {c["id"]: c for c in _read_jsonl(SEED_COMP)}

    new_mcq: list[dict] = []
    new_comp: list[dict] = []
    rejects: dict[str, int] = {g: 0 for g in REJECT_GATES}
    candidates = 0
    seeds_covered = 0
    for i, seed in enumerate(chosen, 1):
        accepted_for_seed = 0
        for n in range(1, args.k + 1):
            candidates += 1
            r = eval_reword(client, seed, n - 1)
            if r.get("accepted"):
                accepted_for_seed += 1
                rec = _record(seed, n, r["statement"])
                new_mcq.append(rec)
                comp = _companion(seed_comps, rec["id"], seed)
                if comp is not None:
                    new_comp.append(comp)
            elif r.get("reject"):
                rejects[r["reject"]] = rejects.get(r["reject"], 0) + 1
        if accepted_for_seed:
            seeds_covered += 1
        print(f"  [{i}/{len(chosen)}] seed {seed.id:10} accepted={accepted_for_seed}/{args.k}")

    # Idempotent merge: keep any non-reworded generated items + non-RW# companions.
    keep_mcq = [r for r in _read_jsonl(GEN_MCQ) if r.get("source") != "reworded"]
    keep_comp = [c for c in _read_jsonl(GEN_COMP) if not str(c.get("id", "")).startswith("RW#")]
    with open(GEN_MCQ, "w", encoding="utf-8") as f:
        for r in keep_mcq + new_mcq:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(GEN_COMP, "w", encoding="utf-8") as f:
        for c in keep_comp + new_comp:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\nwrote {len(new_mcq)} reworded variants -> {os.path.relpath(GEN_MCQ, REPO)} "
          f"(kept {len(keep_mcq)} non-reworded)")
    print(f"wrote {len(new_comp)} reworded companions -> {os.path.relpath(GEN_COMP, REPO)}")
    print(f"(OpenAI calls: {client.calls}).  Next: python speedrun/promote_generated.py")

    summary = {
        "seeds": len(chosen), "candidates": candidates, "accepted": len(new_mcq),
        "rejects": rejects, "seeds_covered": seeds_covered, "companions": len(new_comp),
    }
    if not print_report(summary):
        print("REWORD GATE: nothing accepted from a non-empty seed set.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
