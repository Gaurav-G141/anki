# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Baseline comparison (assignment §2 / Friday): the AI must BEAT a simpler method.

The AI capability under test is **answering a novel Physics-GRE MCQ** — the blind
GPT-4o solver that grounds the Heuristic Coach and powers the Phase-2 generator's
consensus gate (``gen_prompts.build_solver_prompt``). We put it head-to-head, on the
SAME held-out split, against two "simpler methods" the rubric names:

  * keyword search  — TF/token nearest-neighbour over the DEV problems (Jaccard on
    statement+choice tokens); predict the neighbour's answer letter.
  * vector search   — hashed bag-of-words cosine nearest-neighbour over DEV; predict
    the neighbour's answer letter.
  * random          — 1/5 = 20%, printed for reference.

Retrieval corpus = DEV problems (num<=45, answers "known"); test = HELD problems
(num>45). Dev/held are disjoint and near-dup-checked (see ``leakage_check.py``), so a
query never retrieves itself — no leakage. Metric = answer accuracy on the test split.

Offline for the baselines; the AI column needs an OpenAI key (``.env``). Use
``--dry-run`` to compute the keyword/vector/random columns with no API calls.

    out/pyenv/bin/python speedrun/baseline_eval.py --split held
    out/pyenv/bin/python speedrun/baseline_eval.py --split held --dry-run   # no AI column
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "speedrun"))

import gen_prompts as G  # noqa: E402
from heuristic_eval import (  # noqa: E402
    DEFAULT_MODEL,
    DEV_MAX_NUM,
    OpenAIClient,
    get_key,
)
from leakage_check import _tokens  # noqa: E402
from pgre_problems import load_gr9277_with_choices  # noqa: E402

RANDOM_BASELINE = 0.20  # 1 of 5 choices

# hashed bag-of-words dimensionality for the vector baseline
_VEC_DIM = 4096


def _text(p) -> str:
    """The retrieval text for a problem: statement + all choice texts."""
    return p.statement + " " + " ".join(t for _, t in p.choices)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _vec(tokens) -> dict[int, float]:
    v: dict[int, float] = {}
    for tok in tokens:
        h = zlib.crc32(tok.encode("utf-8")) % _VEC_DIM  # deterministic (not PYTHONHASHSEED)
        v[h] = v.get(h, 0.0) + 1.0
    return v


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(w * b.get(i, 0.0) for i, w in a.items())
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def keyword_predict(query, corpus) -> str:
    """Nearest DEV problem by token Jaccard → its answer letter."""
    qt = _tokens(_text(query))
    best, best_sim = None, -1.0
    for c, ct in corpus:
        sim = _jaccard(qt, ct)
        if sim > best_sim:
            best, best_sim = c, sim
    return best.answer if best else ""


def vector_predict(query, corpus_vecs) -> str:
    """Nearest DEV problem by hashed bag-of-words cosine → its answer letter."""
    qv = _vec(_tokens(_text(query)))
    best, best_sim = None, -1.0
    for c, cv in corpus_vecs:
        sim = _cosine(qv, cv)
        if sim > best_sim:
            best, best_sim = c, sim
    return best.answer if best else ""


def ai_predict(client, prob) -> str:
    """GPT-4o blind solver (statement+choices only, answer withheld) → its letter."""
    q = {"statement": prob.statement, "choices": [[l, t] for l, t in prob.choices]}
    out = client.chat_json(G.build_solver_prompt(q), temperature=0.0)
    return str(out.get("answer", "")).strip().upper()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "held", "all"], default="held")
    ap.add_argument("--limit", type=int, default=0, help="cap test problems (0 = all)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="baselines only; no AI/API")
    args = ap.parse_args()

    seeds = load_gr9277_with_choices()
    dev = [p for p in seeds if p.num <= DEV_MAX_NUM]
    held = [p for p in seeds if p.num > DEV_MAX_NUM]
    test = {"dev": dev, "held": held, "all": seeds}[args.split]
    # Retrieval corpus is always DEV (the "known-answer" set); never includes a
    # held-out test item, so there is no leakage. For --split dev/all we still
    # retrieve from dev but exclude the query itself.
    if args.limit:
        test = test[: args.limit]

    print(
        f"problems: {len(seeds)} (dev {len(dev)} / held {len(held)}); "
        f"test split='{args.split}' ({len(test)}); retrieval corpus=DEV ({len(dev)})"
    )

    corpus_kw = [(c, _tokens(_text(c))) for c in dev]
    corpus_vec = [(c, _vec(_tokens(_text(c)))) for c in dev]

    client = None
    if not args.dry_run:
        client = OpenAIClient(get_key(), args.model)

    kw_ok = vec_ok = ai_ok = ai_err = 0
    n = 0
    for p in test:
        # exclude the query itself from the corpus (matters for --split dev/all)
        kw_corpus = [(c, t) for c, t in corpus_kw if c.id != p.id]
        vec_corpus = [(c, v) for c, v in corpus_vec if c.id != p.id]
        gold = p.answer.upper()
        kw = keyword_predict(p, kw_corpus).upper()
        vec = vector_predict(p, vec_corpus).upper()
        kw_ok += kw == gold
        vec_ok += vec == gold
        if client is not None:
            try:
                ai = ai_predict(client, p)
            except RuntimeError:
                ai, ai_err = "", ai_err + 1  # one flaky call must not abort the run
            ai_ok += ai == gold
        n += 1

    def pct(x: int) -> str:
        return f"{x}/{n} = {x / n:.0%}" if n else "n/a"

    print("\n" + "=" * 62)
    print("BASELINE COMPARISON — answer a novel PGRE MCQ (accuracy)")
    print("=" * 62)
    if client is not None:
        err = f"  ({ai_err} call error(s), counted as misses)" if ai_err else ""
        print(f"  AI (GPT-4o blind solver) ... {pct(ai_ok)}{err}")
    else:
        print("  AI (GPT-4o blind solver) ... [skipped: --dry-run]")
    print(f"  keyword search (Jaccard) ... {pct(kw_ok)}")
    print(f"  vector search (BoW cosine) . {pct(vec_ok)}")
    print(f"  random (1/5) ............... {RANDOM_BASELINE:.0%}")
    if client is not None and n:
        best_base = max(kw_ok, vec_ok) / n
        verdict = "PASS" if ai_ok / n > best_base else "FAIL"
        print(f"\n  --> AI beats the best simpler method: {verdict} "
              f"({ai_ok / n:.0%} vs {best_base:.0%})")
    print(f"(OpenAI calls: {client.calls if client else 0})")


if __name__ == "__main__":
    main()
