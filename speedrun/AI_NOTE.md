# AI note — what we built, why, and what we skipped

_(Friday deliverable: "a short note on what AI you built, why, and what you skipped."
Consolidates what was previously spread across `heuristic_coach.py`,
`HUMAN_MADE_Ai_plan.md`, and `PRD.md`. Last updated 2026-07-05.)_

## What the AI is

1. **Heuristic Coach (Stage 2, shipped in both apps).** In the ⚛️ Practice MCQs
   screen the student picks a letter **and** types, in words, _how_ they'd solve it.
   GPT-4o grades the **approach** — `optimal` / `valid_slower` / `overcomputed` /
   `guessed` / `flawed` — against a validated optimal-approach key, and returns warm,
   second-person feedback plus any fast elimination they missed. An input guard
   (offline tripwire + a model category) catches prompt-injection, abuse, and
   empty/off-topic text so it's never graded as physics.
   Code: `qt/aqt/heuristic_coach.py`, `mobile/SpeedrunApp/Sources/HeuristicCoach.swift`.

   **Grader calibration fix (2026-07-05).** The coach was over-returning `flawed`
   ("⚠️ Reasoning slip") on answers that were _correct with valid core reasoning_, and it
   flipped run-to-run. Fixed with a rubric guard — **a correct pick with valid core reasoning
   can never be graded `flawed`** (at most `valid_slower` / `overcomputed`) — plus **grading
   temperature set to 0** for determinism (was 0.2), and a copied `missed` example removed. The
   fix is synced across desktop (`heuristic_coach.py`) and iOS (`HeuristicCoach.swift`). The
   Andy tutor stays at temperature **0.2** (temperature is parameterized per call). Verified:
   correct→optimal (3/3), wrong+error→flawed (3/3).

2. **Optimal-approach key (Stage 1, offline eval).** `speedrun/heuristic_eval.py`
   built the key the coach grades against: for each real GR9277 problem it produced a
   fast expert approach, **answer-gated deterministically** (the model is given the
   scraped answer and must reproduce it — wrong-answer records are never emitted),
   judged **equal-or-better than the community solution**, with an elimination
   _verifier-as-filter_ (bad eliminations are stripped, 0 shipped) and a clarity check.

3. **Question generator / AI card check (Phase 2 / §7f, offline).** `speedrun/gen_eval.py`
   regenerates and re-validates the PGRE MCQ bank: each item passes a **3-solver blind
   consensus** (3 independent GPT-4o solves must agree with the claimed answer) plus
   single-correct, soundness, novelty, and self-containment gates against pre-declared
   `CUTOFFS`; any item that fails is dropped. It ships **0 ambiguous / 0 unsound by
   construction**. Current bank: **46 items (15 novel + 31 reworded)**, re-run clean
   2026-07-05; bundled into both apps (`pgre_mcq_generated.json`).

   **Honest limitation:** "correctness" here is **consensus-substituted** — the 3-solver
   agreement stands in for a ground-truth key. It is **not** validated against a 50-item
   human gold set, so we deliberately do **not** state a card-correctness accuracy %. What we
   can claim is the by-construction guarantee (0 ambiguous / 0 unsound) and that generation is
   leakage-free (`gen_leakage_check.py`: novel items <0.6 Jaccard vs 399 real problems;
   reworded within [0.15, 0.75) of their seed).

## Why

Memory (Anki's FSRS) is not performance. Recalling a card ≠ solving a _new_ exam
question _fast enough_. The coach builds the memory→performance bridge by teaching the
exam heuristics that make students faster (process-of-elimination, dimensional
analysis, estimation, limiting cases, symmetry) and by flagging over-solving. The
generator widens the practice pool past the finite set of real problems.

## Named source (every AI output traces back)

- **Conquering the Physics GRE** (Kahn, Anderson, & Reece) — encoded as
  `speedrun/heuristic_prompts.HEURISTIC_TOOLKIT`, the grounding for every coach
  judgment.
- **Scraped GR9277 problems + community solutions** (grephysics.net) — the answer key
  and the baseline the Stage-1 approaches must equal-or-beat.
  Nothing the coach shows is ungrounded: with AI off it shows the precomputed key entry.

**Source-traceability status (2026-07-05):** every coach judgment is grounded in the
`HEURISTIC_TOOLKIT` (Kahn/Anderson/Reece) and every graded item traces to a scraped GR9277
problem + community solution; grounding is enforced at the prompt/key layer and re-run clean this
session. Not yet done: a machine-checkable per-output citation trail (each shown tip linked to a
specific toolkit section, surfaced as a UI click-through) — grounding is currently at the
prompt/key level, not exposed as a citation.

## How it's checked

- **Held-out eval with a cutoff:** `heuristic_eval.py` splits GR9277 into dev (num≤45)
  and held-out (num>45); pre-declared `CUTOFFS` (answer 100% by construction,
  equal-or-better ≥0.90, 0 hallucinated eliminations, clarity ≥0.90). Runs before any
  student sees output.
- **Beats a simpler method:** `speedrun/baseline_eval.py` puts the AI blind solver
  head-to-head with **keyword** and **vector** search on the held-out split — see
  [`BASELINE_COMPARISON.md`](./BASELINE_COMPARISON.md).
- **Leakage:** `leakage_check.py` / `gen_leakage_check.py` → CLEAN (dev/held disjoint,
  no near-duplicates, no exam content baked into prompts).
- **Input safety:** `guard_eval.py` (injection/abuse/empty caught; tripwires offline).

## What we skipped (honestly)

- **Live readiness-score calibration.** We do not have longitudinal student
  study→practice-test data in a week, so the Readiness score is shown with a range +
  coverage + confidence and **discloses that its projection is uncalibrated** rather
  than faking a calibrated number (per the assignment's §9 guidance).
- **In-app API-key entry.** For testing, the key is **baked at build time** (desktop
  `pgre_ai_key.txt`, iOS `openai_key.txt`) — plaintext in the artifact, dedicated
  low-quota key, to be replaced with Keychain/secure entry before real distribution.
- **Live in-app generation.** The generator runs offline (Stage 1); generated
  questions ship as a pre-validated bank, not generated on-device at runtime.
- **AI off is always safe:** both apps run fully with no key — the coach shows the
  precomputed optimal approach and never fabricates a grade.
