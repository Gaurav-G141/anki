# Model descriptions (Speedrun §10 — one page per model, with the give-up rule)

This fork reports **three** honest scores from one read-only Rust RPC
(`SpeedrunService.TopicMastery`, [rslib/src/speedrun/mod.rs](../rslib/src/speedrun/mod.rs)),
served identically to the desktop (PyO3) and iOS (C-FFI) apps. Every score ships with a
**range** and a **confidence**, and every score **abstains** ("give up") independently when
its own data is too thin — never a confident point number on sparse data.

Held-out evidence for these models lives in:

- **Memory calibration** — [`calibration_eval.py`](calibration_eval.py) → Brier / log-loss /
  ECE + reliability chart ([`calibration_chart.svg`](calibration_chart.svg)).
- **Performance generalization** — [`paraphrase_eval.py`](paraphrase_eval.py) → solver accuracy
  on original vs reworded held-out questions.
- **Feature value** — [`ablation.py`](ablation.py) → three-arm study-feature ablation.

---

## 1. Memory model

- **Question it answers:** _How much of the material do you currently retain?_
- **Inputs:** each PGRE-tagged card's FSRS `memory_state` (stability, difficulty), the card's
  decay, and time since last review — all owned by the Rust core.
- **Method:** for each card, the FSRS forgetting curve gives current retrievability
  `R = (1 + (0.9^(-1/decay) − 1)·t/S)^(−decay)` (`fsrs` crate `current_retrievability_seconds`).
  A card is **mastered** iff `R ≥ 0.90` (`DEFAULT_MASTERED_THRESHOLD`). The **memory score** is
  the mastered fraction across covered cards.
- **Range:** a **Wilson 95%** interval on the mastered fraction (not a naïve ±). Reported as
  `score (low–high)`.
- **Give-up rule (abstains when ANY holds):** fewer than **20** reviewed cards
  (`DEFAULT_REVIEW_FLOOR`); subject **coverage < 0.40** (`DEFAULT_COVERAGE_FLOOR`); a
  high-weight subject has **no** cards; or **no** cards carry FSRS state. On abstain it returns
  reasons, not a number.
- **Calibration (held-out evidence):** the recall probabilities the model emits are calibrated —
  on a held-out review slice, **Brier 0.141**, **log-loss 0.445**, **ECE 0.031** (target
  Brier ≤ 0.20, ECE ≤ 0.10; all met). Reliability curve tracks the diagonal with mild
  mid-range overconfidence. The eval's forgetting-curve is asserted to match the engine's own
  `fsrs-5.2.0` test vectors to 1e-4, so it calibrates the _shipped_ model. (`calibration_eval.py`;
  no real multi-month logs exist yet, so this runs a deterministic learner simulation — see that
  file's header for the two anti-circularity safeguards.)

## 2. Performance model

- **Question it answers:** _On the material you have reviewed, how accurately do you perform?_
- **Inputs:** graded `revlog` rows for PGRE cards (`ease` = grade), per subject.
- **Method:** demonstrated recall accuracy = fraction of graded reviews answered **Good or
  better** (`ease ≥ 3`), aggregated with subject weights.
- **Range:** **Wilson 95%** interval on that accuracy.
- **Give-up rule:** independent of Memory — needs graded reviews **and** coverage, but **not**
  FSRS state (so Performance can score when Memory abstains, and vice-versa).
- **Scope honesty (held-out evidence):** Performance is accuracy on _reviewed_ material — **not**
  a held-out generalization guarantee. The generalization proof is the **paraphrase eval**: a
  blind GPT-4o solver scores **79% on original** held-out GR9277 items (19/24) vs **81% on
  reworded** versions (39/48; same physics, changed surface) — a **~0-point** gap, i.e. it solves
  the physics rather than recalling seen items. Integrity-gated (rewords must actually differ; no
  answer leakage). (`paraphrase_eval.py`.)

## 3. Readiness model

- **Question it answers:** _What PGRE scaled score would you project right now?_
- **Inputs:** the Performance accuracy (above) and subject coverage.
- **Method:** a **documented linear anchor** mapping accuracy → the PGRE scale:
  `200 + accuracy·790`, snapped to the real **10-point** grid, clamped to **[200, 990]**.
- **Range:** the Wilson-mapped band **widened by a coverage penalty** — low coverage → a
  deliberately **wide** range and a confidence **capped below "high"**. Never a confident point
  number.
- **Give-up rule:** derived from Performance — abstains whenever Performance abstains.
- **Honesty note:** the PGRE reports a single 200–990 scaled score (no official ETS subscores);
  this fork tracks 9 weighted subjects **internally** for coverage/mastery but projects one
  ranged readiness number, consistent with the README.

---

### Why three scores, not one blended number

They answer different questions and fail independently: you can retain a lot but perform
inconsistently, or perform well on a thin slice you haven't broadly covered. Blending them
would hide exactly the uncertainty the give-up rules exist to surface. Cannot-break rule #3
(three separate ranged scores) is enforced structurally — the TS honesty guard makes a
range-less score impossible, and the iOS `ScoresView` ports the same logic.

_See also:_ [RUST_CHANGE.md](RUST_CHANGE.md) (the engine change + why-Rust),
[FRIDAY_GAPS.md](FRIDAY_GAPS.md) (wiring points), [COMPREHENSIVE_TEST_REPORT.md](COMPREHENSIVE_TEST_REPORT.md)
(full results incl. the held-out evals above).
