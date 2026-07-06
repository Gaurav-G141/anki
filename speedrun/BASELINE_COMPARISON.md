# Baseline comparison — AI vs a simpler method

_Friday / rule §2: "Every AI output ... must beat a simpler method (keyword or
vector search)." Reproduce with `just baseline-eval -- --split held` (or
`out/pyenv/bin/python speedrun/baseline_eval.py --split held`)._

## Task

**Answer a novel Physics-GRE MCQ** (pick the correct letter). This is the AI
capability under test — the blind GPT-4o solver (`gen_prompts.build_solver_prompt`)
that grounds the Heuristic Coach and powers the Phase-2 generator's consensus gate.

## Setup (fair + leakage-free)

- **Test split:** held-out GR9277 problems (`num > 45`), 47 items.
- **Retrieval corpus for the baselines:** the DEV problems (`num ≤ 45`, 43 items) —
  the "known-answer" set. Dev/held are disjoint and near-duplicate-checked
  (`leakage_check.py`), so a query never retrieves itself. No leakage.
- **Metric:** answer accuracy on the 47 held-out problems.
- Methods compared:
  - **AI** — GPT-4o blind solver (statement + choices only, answer withheld).
  - **Keyword search** — nearest DEV problem by token Jaccard (statement + choices);
    predict that neighbour's answer letter.
  - **Vector search** — nearest DEV problem by hashed bag-of-words cosine; predict
    that neighbour's answer letter.
  - **Random** — 1/5 = 20%, for reference.

## Result (2026-07-05, gpt-4o, held-out GR9277 num>45, n=47)

| Method                       | Accuracy        |
| ---------------------------- | --------------- |
| **AI (GPT-4o blind solver)** | **31/47 = 66%** |
| Keyword search (Jaccard)     | 13/47 = 28%     |
| Vector search (BoW cosine)   | 11/47 = 23%     |
| Random (1/5)                 | 20%             |

**Verdict: PASS** — the AI beats the best simpler method **66% vs 28%** (≈2.4×), and
both retrieval baselines are barely above chance. (One of the 47 AI calls hit a
network timeout and was counted **as a miss**, so the true AI accuracy is a touch
higher; we report the conservative number.)

## Why the baselines are weak (and this is the right comparison)

Keyword/vector search can only return _another_ problem's answer. Two PGRE problems
that share surface vocabulary (same subject, similar symbols) almost never share the
same correct letter, so retrieval lands near chance. Real physics reasoning — the AI
— is what actually transfers. This is exactly the memory→performance bridge the
assignment asks for: recall/lookup is not the same as solving a new question.
