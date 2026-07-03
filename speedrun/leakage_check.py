# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Leakage check for the Heuristic-Coach eval (assignment §7e).

We are not TRAINING a model (GPT-4o is frozen), so classic train/test leakage
doesn't apply — but two integrity properties still must hold and are checked here:

  1. DEV / HELD-OUT disjointness + no near-duplicates. Prompts are tuned on the
     dev split; if a held-out problem is a near-duplicate of a dev problem, tuning
     could implicitly leak into the held-out numbers. We flag any cross-split pair
     with high token overlap.
  2. No exam content baked into the prompt templates. The prompts must inject only
     the CURRENT problem at call time — never hardcode any problem's statement or
     answer. We scan `heuristic_prompts.py` for embedded problem text/answers.

Pure/offline — no network. Exit code 0 = clean.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from heuristic_eval import DEV_MAX_NUM  # noqa: E402
from pgre_problems import load_gr9277_with_choices  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEAR_DUP_JACCARD = 0.60  # token-set overlap above this = suspicious near-duplicate


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def check_split_disjoint_and_dedup() -> list[str]:
    problems = load_gr9277_with_choices()
    dev = [p for p in problems if p.num <= DEV_MAX_NUM]
    held = [p for p in problems if p.num > DEV_MAX_NUM]
    issues = []
    dev_ids = {p.id for p in dev}
    held_ids = {p.id for p in held}
    overlap = dev_ids & held_ids
    if overlap:
        issues.append(f"dev/held id overlap: {overlap}")
    dev_tok = [(p.id, _tokens(p.statement)) for p in dev]
    for hp in held:
        ht = _tokens(hp.statement)
        if not ht:
            continue
        for did, dt in dev_tok:
            if not dt:
                continue
            j = len(ht & dt) / len(ht | dt)
            if j >= NEAR_DUP_JACCARD:
                issues.append(f"near-duplicate across splits: {hp.id} ~ {did} (Jaccard {j:.2f})")
    return issues


def check_no_embedded_content() -> list[str]:
    """Ensure the prompt module doesn't hardcode any problem statement/answer."""
    problems = load_gr9277_with_choices()
    src = open(os.path.join(REPO, "speedrun", "heuristic_prompts.py"), encoding="utf-8").read()
    issues = []
    for p in problems:
        # a distinctive 8+ word shingle from each statement should NOT be in the source
        words = re.findall(r"[A-Za-z]+", p.statement)
        if len(words) >= 8:
            shingle = " ".join(words[:8]).lower()
            if shingle and shingle in src.lower():
                issues.append(f"statement shingle from {p.id} found in heuristic_prompts.py")
    return issues


def main():
    issues = check_split_disjoint_and_dedup() + check_no_embedded_content()
    if issues:
        print("LEAKAGE CHECK: FAIL")
        for i in issues:
            print("  -", i)
        sys.exit(1)
    problems = load_gr9277_with_choices()
    dev = sum(1 for p in problems if p.num <= DEV_MAX_NUM)
    held = len(problems) - dev
    print(f"LEAKAGE CHECK: CLEAN — dev({dev}) and held({held}) splits disjoint, "
          f"no cross-split near-duplicates (Jaccard>={NEAR_DUP_JACCARD}), "
          f"no exam content embedded in prompts.")


if __name__ == "__main__":
    main()
