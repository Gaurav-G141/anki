# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Leakage / novelty check for the Phase-2 generated MCQ bank.

The generator (``gen_eval.py``) writes only items that passed a deterministic
novelty gate at generation time, but this is the independent post-hoc assertion
over the SHIPPED bank (``speedrun/data/generated_mcq.jsonl``).

**NOVEL items** (``source != "reworded"`` — the Phase-2 generated variants):

  1. Every item is < 0.60 token-Jaccard vs ALL 399 real problems.
  2. Every item is < 0.60 token-Jaccard vs every OTHER novel item.
  3. No statement copied a real one verbatim (first-8-word shingle absent from any
     real problem statement).

**REWORDED items** (``source == "reworded"`` — same-physics surface rewordings; a
reword is SUPPOSED to overlap its seed, so the 0.60 novelty gate does NOT apply).
Instead each reword must:

  4. sit inside the paraphrase band vs its ``seed_id`` statement:
     ``REWORD_MIN_SIM (0.15) <= Jaccard < REWORD_MAX_SIM (0.75)`` — actually changed
     surface, still the same problem; and
  5. be distinct from its sibling rewordings (not a near-identical copy).

Pure/offline — no network. Exit code 0 = clean (and 0 = no bank yet).
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from leakage_check import NEAR_DUP_JACCARD, _tokens  # noqa: E402
from paraphrase_eval import REWORD_MAX_SIM, REWORD_MIN_SIM  # noqa: E402
from pgre_problems import load_all  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(REPO, "speedrun", "data", "generated_mcq.jsonl")
REAL_BANK = os.path.join(REPO, "qt", "aqt", "data", "pgre_mcq.json")
SIBLING_MAX_SIM = 0.95  # two rewordings of the same seed must not be near-identical


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_bank(path: str) -> list[dict]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _seed_statements() -> dict[str, str]:
    """Seed statements by id, from the shipped real bank (the reword source of truth)."""
    try:
        bank = json.load(open(REAL_BANK, encoding="utf-8"))["questions"]
    except (OSError, ValueError, KeyError):
        return {}
    return {q["id"]: q.get("statement", "") for q in bank}


def check(items: list[dict]) -> list[str]:
    issues = []
    novel = [it for it in items if it.get("source") != "reworded"]
    reworded = [it for it in items if it.get("source") == "reworded"]

    real = load_all()
    real_tok = [(p.id, _tokens(p.statement)) for p in real]
    real_lower = [p.statement.lower() for p in real]

    # --- NOVEL items: the full 0.60 novelty gates ---
    gen_tok = [(it.get("id", f"item{i}"), _tokens(it.get("statement", ""))) for i, it in enumerate(novel)]
    for gid, gt in gen_tok:  # 1) vs all real problems
        for rid, rt in real_tok:
            j = _jaccard(gt, rt)
            if j >= NEAR_DUP_JACCARD:
                issues.append(f"near-duplicate of real: {gid} ~ {rid} (Jaccard {j:.2f})")
    for a in range(len(gen_tok)):  # 2) vs each other
        for b in range(a + 1, len(gen_tok)):
            j = _jaccard(gen_tok[a][1], gen_tok[b][1])
            if j >= NEAR_DUP_JACCARD:
                issues.append(f"near-duplicate among generated: {gen_tok[a][0]} ~ {gen_tok[b][0]} (Jaccard {j:.2f})")
    for it in novel:  # 3) verbatim shingle of a real statement
        words = re.findall(r"[A-Za-z]+", it.get("statement", ""))
        if len(words) >= 8:
            shingle = " ".join(words[:8]).lower()
            if any(shingle in rl for rl in real_lower):
                issues.append(f"verbatim first-8-word shingle from {it.get('id')} found in a real problem")

    # --- REWORDED items: paraphrase band vs seed + sibling distinctness ---
    seeds = _seed_statements()
    by_seed: dict[str, list[tuple[str, set[str]]]] = {}
    for it in reworded:
        rid, sid = it.get("id", "?"), it.get("seed_id", "")
        rt = _tokens(it.get("statement", ""))
        seed_stmt = seeds.get(sid)
        if not seed_stmt:
            issues.append(f"reworded {rid}: seed_id {sid!r} not found in the real bank")
            continue
        j = _jaccard(rt, _tokens(seed_stmt))
        if j >= REWORD_MAX_SIM:
            issues.append(f"reworded {rid}: too close to seed {sid} (Jaccard {j:.2f} >= {REWORD_MAX_SIM})")
        if j < REWORD_MIN_SIM:
            issues.append(f"reworded {rid}: unrelated to seed {sid} (Jaccard {j:.2f} < {REWORD_MIN_SIM})")
        by_seed.setdefault(sid, []).append((rid, rt))
    for sid, sibs in by_seed.items():  # 5) siblings not near-identical
        for a in range(len(sibs)):
            for b in range(a + 1, len(sibs)):
                j = _jaccard(sibs[a][1], sibs[b][1])
                if j >= SIBLING_MAX_SIM:
                    issues.append(f"reworded siblings near-identical: {sibs[a][0]} ~ {sibs[b][0]} (Jaccard {j:.2f})")
    return issues


def main():
    if not os.path.exists(BANK):
        print(f"GEN LEAKAGE CHECK: no bank yet at {BANK} — nothing to check (run gen_eval.py first).")
        sys.exit(0)
    items = load_bank(BANK)
    issues = check(items)
    if issues:
        print("GEN LEAKAGE CHECK: FAIL")
        for i in issues:
            print("  -", i)
        sys.exit(1)
    n_rw = sum(1 for it in items if it.get("source") == "reworded")
    print(f"GEN LEAKAGE CHECK: CLEAN — {len(items)} item(s) [{len(items) - n_rw} novel, {n_rw} reworded]: "
          f"novel < {NEAR_DUP_JACCARD} Jaccard vs 399 real problems and each other (no verbatim copies); "
          f"reworded within [{REWORD_MIN_SIM}, {REWORD_MAX_SIM}) of their seed and distinct from siblings.")


if __name__ == "__main__":
    main()
