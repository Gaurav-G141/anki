# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Leakage / novelty check for the Phase-2 generated MCQ bank.

The generator (``gen_eval.py``) writes only items that passed a deterministic
novelty gate at generation time, but this is the independent post-hoc assertion
over the SHIPPED bank (``speedrun/data/generated_mcq.jsonl``):

  1. Every generated item is < 0.60 token-Jaccard vs ALL 399 real problems.
  2. Every generated item is < 0.60 token-Jaccard vs every OTHER generated item.
  3. No generated statement copied a real one verbatim (its first-8-word shingle
     does not appear inside any real problem statement).

Pure/offline — no network. Exit code 0 = clean (and 0 = no bank yet).
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from leakage_check import NEAR_DUP_JACCARD, _tokens  # noqa: E402
from pgre_problems import load_all  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(REPO, "speedrun", "data", "generated_mcq.jsonl")


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


def check(items: list[dict]) -> list[str]:
    issues = []
    real = load_all()
    real_tok = [(p.id, _tokens(p.statement)) for p in real]
    real_lower = [p.statement.lower() for p in real]

    gen_tok = [(it.get("id", f"item{i}"), _tokens(it.get("statement", ""))) for i, it in enumerate(items)]

    # 1) vs all real problems
    for gid, gt in gen_tok:
        for rid, rt in real_tok:
            j = _jaccard(gt, rt)
            if j >= NEAR_DUP_JACCARD:
                issues.append(f"near-duplicate of real: {gid} ~ {rid} (Jaccard {j:.2f})")

    # 2) vs each other
    for a in range(len(gen_tok)):
        for b in range(a + 1, len(gen_tok)):
            j = _jaccard(gen_tok[a][1], gen_tok[b][1])
            if j >= NEAR_DUP_JACCARD:
                issues.append(f"near-duplicate among generated: {gen_tok[a][0]} ~ {gen_tok[b][0]} (Jaccard {j:.2f})")

    # 3) verbatim shingle of a real statement
    for it in items:
        words = re.findall(r"[A-Za-z]+", it.get("statement", ""))
        if len(words) >= 8:
            shingle = " ".join(words[:8]).lower()
            for rl in real_lower:
                if shingle in rl:
                    issues.append(f"verbatim first-8-word shingle from {it.get('id')} found in a real problem")
                    break
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
    print(f"GEN LEAKAGE CHECK: CLEAN — {len(items)} generated item(s), all < {NEAR_DUP_JACCARD} "
          f"Jaccard vs 399 real problems and vs each other, no verbatim statement copies.")


if __name__ == "__main__":
    main()
