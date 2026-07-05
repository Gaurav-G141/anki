# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Held-out PARAPHRASE eval for the AI physics solver (assignment §7d / §9 Step 2).

The question this answers: does the AI *solve the physics*, or does it just recall
the answer to a released GR9277 item it has effectively seen? We take the HELD-OUT
split (num > DEV_MAX_NUM — never used to tune any prompt), reword each problem's
statement two ways (same numbers, same choices, same correct letter — only the
surface prose changes), and compare the blind solver's accuracy on the ORIGINAL vs
the REWORDED versions. A small gap = genuine generalization; a large drop = the
original score was inflated by memorization.

Integrity gates (hard — exit non-zero):
  * every reword must actually differ from the original (Jaccard < REWORD_MAX_SIM),
    else it's a no-op copy and the test is meaningless;
  * a reword must not collapse to near-nothing (min token overlap with the original,
    so it still describes the same problem);
  * no answer letter leaked into a reworded stem.

The accuracy gap itself is REPORTED honestly (a large gap is a valid negative result,
not a crash). Reuses the exact OpenAI plumbing from ``heuristic_eval`` and the blind
solver prompt from ``gen_prompts``. Key from ``.env`` (see heuristic_eval); ``--dry-run``
validates offline with no API calls.

    out/pyenv/bin/python speedrun/paraphrase_eval.py --help
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "speedrun"))

import gen_prompts as G  # noqa: E402
from heuristic_eval import DATA_DIR, DEV_MAX_NUM, OpenAIClient, get_key  # noqa: E402
from leakage_check import _tokens  # noqa: E402  (shared tokenizer for Jaccard)
from pgre_problems import load_gr9277_with_choices  # noqa: E402

OUT_PATH = os.path.join(DATA_DIR, "paraphrase_eval.json")
DEFAULT_MODEL = "gpt-4o"

# Held-out sizing + reword integrity thresholds (pre-declared).
DEFAULT_N = 30            # held-out problems to test (0 = all held-out)
REWORDS_PER = 2           # reword variants per problem
REWORD_MAX_SIM = 0.75     # Jaccard(orig, reword) must be BELOW this (surface changed)
REWORD_MIN_SIM = 0.15     # ...and ABOVE this (still the same problem, not gibberish)

# Pre-declared success criteria for the REPORTED accuracy numbers.
CUTOFFS = {
    "reworded_accuracy_min": 0.50,   # solver must still clear this on reworded items
    "max_accuracy_drop": 0.20,       # original - reworded accuracy must not exceed this
}


def _solve(client: OpenAIClient, statement: str, choices) -> str:
    """Run the blind solver on a (statement, choices) pair; return its letter A-E."""
    q = {"statement": statement, "choices": choices}
    out = client.chat_json(G.build_solver_prompt(q))
    return str(out.get("answer", "")).strip().upper()[:1]


def _reword(client: OpenAIClient, prob, variant: int) -> str:
    out = client.chat_json(G.build_paraphrase_prompt(prob, variant), temperature=0.7)
    return str(out.get("statement", "")).strip()


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _reword_issues(prob, reworded: str) -> list[str]:
    """Integrity checks on one reworded stem (empty list = clean)."""
    issues = []
    if len(reworded.split()) < 4:
        issues.append("reword too short / degenerate")
        return issues
    j = _jaccard(prob.statement, reworded)
    if j >= REWORD_MAX_SIM:
        issues.append(f"reword too similar to original (Jaccard {j:.2f} >= {REWORD_MAX_SIM})")
    if j < REWORD_MIN_SIM:
        issues.append(f"reword unrelated to original (Jaccard {j:.2f} < {REWORD_MIN_SIM})")
    # answer-letter leak: a bare "(A)".."(E)" or "answer is X" in the stem
    import re
    if re.search(r"\banswer\b", reworded, re.I) or re.search(r"\(([A-E])\)", reworded):
        issues.append("reworded stem appears to reference an answer/choice letter")
    return issues


def evaluate(client: OpenAIClient, problems: list) -> dict:
    per = []
    orig_correct = orig_n = 0
    reword_correct = reword_n = 0
    integrity_issues: list[str] = []

    for i, prob in enumerate(problems, 1):
        rec: dict = {"id": prob.id, "answer": prob.answer, "subject": prob.subject_key}
        # 1) solver on the ORIGINAL
        o = _solve(client, prob.statement, prob.choices)
        o_ok = o == prob.answer.upper()
        rec["original"] = {"solver": o, "correct": o_ok}
        orig_n += 1
        orig_correct += int(o_ok)

        # 2) rewordings + solver on each
        rec["rewords"] = []
        for v in range(REWORDS_PER):
            reworded = _reword(client, prob, v)
            iss = _reword_issues(prob, reworded)
            entry = {"variant": v, "issues": iss, "jaccard": round(_jaccard(prob.statement, reworded), 3)}
            if iss:
                integrity_issues += [f"{prob.id} v{v}: {m}" for m in iss]
                entry["skipped"] = True
            else:
                r = _solve(client, reworded, prob.choices)
                r_ok = r == prob.answer.upper()
                entry.update({"solver": r, "correct": r_ok, "statement": reworded})
                reword_n += 1
                reword_correct += int(r_ok)
            rec["rewords"].append(entry)
        per.append(rec)
        print(f"  [{i}/{len(problems)}] {prob.id:10} orig={'Y' if o_ok else 'n'} "
              f"reworded={''.join('Y' if w.get('correct') else ('-' if w.get('skipped') else 'n') for w in rec['rewords'])}")

    return {
        "orig_correct": orig_correct, "orig_n": orig_n,
        "reword_correct": reword_correct, "reword_n": reword_n,
        "orig_acc": orig_correct / max(orig_n, 1),
        "reword_acc": reword_correct / max(reword_n, 1),
        "integrity_issues": integrity_issues,
        "per_problem": per,
    }


def print_report(summary: dict) -> bool:
    """Print the report; return True iff integrity is clean AND accuracy criteria met.
    A large accuracy drop is reported honestly but does NOT crash — only integrity
    (a broken reword) and the pre-declared accuracy cutoffs gate the exit code."""
    oa, ra = summary["orig_acc"], summary["reword_acc"]
    drop = oa - ra
    print("\n" + "=" * 70 + "\nPARAPHRASE (held-out generalization) eval\n" + "=" * 70)
    print(f"  original accuracy .......... {summary['orig_correct']}/{summary['orig_n']} = {oa:.0%}")
    print(f"  reworded accuracy .......... {summary['reword_correct']}/{summary['reword_n']} = {ra:.0%}")
    print(f"  accuracy drop (orig-reword)  {drop:+.0%}   (memorization would show a large drop)")
    n_iss = len(summary["integrity_issues"])
    print(f"  reword integrity issues .... {n_iss}")
    for m in summary["integrity_issues"][:8]:
        print(f"      - {m}")
    if n_iss > 8:
        print(f"      … and {n_iss - 8} more")

    integrity_ok = n_iss == 0
    acc_ok = ra >= CUTOFFS["reworded_accuracy_min"] and drop <= CUTOFFS["max_accuracy_drop"]
    print(f"  --> integrity {'CLEAN' if integrity_ok else 'FAIL'}; "
          f"accuracy cutoff {'PASS' if acc_ok else 'NOT MET'} "
          f"(reworded>={CUTOFFS['reworded_accuracy_min']:.0%}, drop<={CUTOFFS['max_accuracy_drop']:.0%})")
    print()
    return integrity_ok and acc_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="held-out problems to test (0 = all held-out)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="no API calls; validate prompts/parsing offline")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    problems = load_gr9277_with_choices()
    held = [p for p in problems if p.num > DEV_MAX_NUM]
    chosen = held if args.n <= 0 else held[: args.n]
    print(f"held-out split: {len(held)} problems (num > {DEV_MAX_NUM}); "
          f"testing {len(chosen)}; rewords/problem={REWORDS_PER}; model={args.model}")

    if args.dry_run:
        p = chosen[0]
        _ = G.build_solver_prompt({"statement": p.statement, "choices": p.choices})
        for v in range(REWORDS_PER):
            _ = G.build_paraphrase_prompt(p, v)
        sample = G.build_paraphrase_prompt(p, 0)
        print(f"\n[dry-run] built solver + {REWORDS_PER} paraphrase prompts for {len(chosen)} problems OK.")
        print(f"[dry-run] sample paraphrase user prompt ({p.id}), first 700 chars:\n{'-'*60}\n"
              f"{sample[1]['content'][:700]}\n{'-'*60}")
        print("[dry-run] no API calls made. Add OPENAI_API_KEY to .env and drop --dry-run to run for real.")
        return

    client = OpenAIClient(get_key(), args.model)
    os.makedirs(DATA_DIR, exist_ok=True)
    summary = evaluate(client, chosen)

    payload = {k: v for k, v in summary.items()}
    payload["cutoffs"] = CUTOFFS
    payload["config"] = {
        "dev_max_num": DEV_MAX_NUM, "rewords_per": REWORDS_PER,
        "reword_max_sim": REWORD_MAX_SIM, "reword_min_sim": REWORD_MIN_SIM,
        "model": args.model,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\nwrote {os.path.relpath(args.out, REPO)}   (OpenAI calls: {client.calls})")

    ok = print_report(summary)
    if not ok:
        print("PARAPHRASE GATE: integrity or accuracy cutoff not met.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
