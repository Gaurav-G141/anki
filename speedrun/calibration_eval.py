# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Held-out CALIBRATION eval for the memory model (assignment §9 Step 1).

The memory model this fork ships emits, per card, a **recall probability** R via the
FSRS forgetting curve — ``topic_mastery`` calls a card "mastered" iff R >= 0.9
(``rslib/src/speedrun/mod.rs`` ``DEFAULT_MASTERED_THRESHOLD``). A probability is only
honest if it is *calibrated*: of all the cards the model says have ~70% recall, ~70%
should actually be recalled. This script measures that with **Brier score**, **log-loss**,
and **expected calibration error (ECE)** on a **held-out** slice of reviews, and draws a
reliability diagram.

We have no multi-month real user history to calibrate against yet, so this runs a
**deterministic simulation** of a spaced-repetition learner and scores the model's R
against realized recall on the learner's last (held-out) reviews. Two things keep it honest
rather than circular:

  1. The model curve is the ENGINE's exact curve. ``power_forgetting_curve`` here is a
     line-for-line port of ``fsrs-5.2.0/src/inference.rs`` ``current_retrievability``
     (R = (1 + (0.9^(-1/decay) - 1)·t/S)^(-decay)); a startup self-check asserts it
     matches the crate's own published test vectors to 1e-4 (so we are calibrating the
     REAL model, not a lookalike).
  2. The learner's TRUE recall differs from the model's belief in the way real data does:
     the model's stability estimate is off by a per-card log-normal error, and a fraction
     of "leech" cards truly forget faster than any state predicts. So the reliability
     diagram can (and does) show where the model is over/under-confident — a real result,
     not a tautology.

Held-out split: per card, the last ``HELDOUT_FRAC`` of reviews are scored; earlier reviews
only advance state. Deterministic (seeded) so ``just`` runs reproduce exactly. Pure/offline,
no Anki, no network, no non-stdlib deps.

    out/pyenv/bin/python speedrun/calibration_eval.py --help
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "speedrun", "data")
OUT_JSON = os.path.join(DATA_DIR, "calibration.json")
OUT_SVG = os.path.join(REPO, "speedrun", "calibration_chart.svg")

# FSRS constants, matching rslib/src/speedrun/mod.rs + fsrs-5.2.0/src/inference.rs.
FSRS5_DEFAULT_DECAY = 0.5
MASTERED_THRESHOLD = 0.9

# Pre-declared calibration targets (a miss is reported honestly as a negative result;
# --strict turns them into a hard gate for CI use).
TARGETS = {"brier_max": 0.20, "log_loss_max": 0.60, "ece_max": 0.10}

N_BINS = 10


# --- the model under test: the engine's forgetting curve ----------------------


def power_forgetting_curve(days_elapsed: float, stability: float, decay: float = FSRS5_DEFAULT_DECAY) -> float:
    """R = (1 + FACTOR·t/S)^(-decay), FACTOR = 0.9^(-1/decay) - 1.

    Line-for-line port of fsrs-5.2.0 `current_retrievability` (inference.rs). Verified
    against the crate's own test vectors in `_assert_engine_parity`."""
    factor = 0.9 ** (1.0 / -decay) - 1.0
    return (days_elapsed / stability * factor + 1.0) ** (-decay)


def _assert_engine_parity() -> None:
    """Fail loudly if our curve drifts from the engine's published test vectors
    (fsrs-5.2.0/src/inference.rs test `power_forgetting_curve`, decay=0.2)."""
    vectors = [(0.0, 1.0), (1.0, 0.9), (2.0, 0.84028935), (3.0, 0.7985001)]
    for t, expected in vectors:
        got = power_forgetting_curve(t, 1.0, decay=0.2)
        if abs(got - expected) > 1e-4:
            raise AssertionError(
                f"forgetting-curve port drifted from engine: R(t={t},S=1,decay=0.2)="
                f"{got:.6f}, engine says {expected:.6f}. Fix the port before trusting calibration."
            )


# --- synthetic learner (ground truth) -----------------------------------------


def _interval_for_retention(stability: float, target: float, decay: float = FSRS5_DEFAULT_DECAY) -> float:
    """Days until predicted recall drops to `target` — the FSRS scheduling inverse of
    the forgetting curve. Used to schedule the learner's next review realistically."""
    factor = 0.9 ** (1.0 / -decay) - 1.0
    return stability / factor * (target ** (-1.0 / decay) - 1.0)


def simulate(rng: random.Random, n_cards: int, reviews_per: int, heldout_frac: float) -> list[dict]:
    """Simulate `n_cards`, each reviewed `reviews_per` times. Returns held-out review
    samples: {predicted (model R), outcome (0/1), stability, days} — one per held-out review.

    Ground truth vs model belief (the two honest mismatches):
      * true stability = model stability × exp(N(0, sigma)) — the model misestimates S.
      * `leech_frac` of cards truly forget ~3× faster than any state says (hard material).
    Recall each review ~ Bernoulli(R_true); a pass grows stability, a lapse shrinks it
    (a standard SRS update), so state and outcomes co-evolve like real study."""
    sigma = 0.55          # log-normal spread of the model's stability-estimate error
    leech_frac = 0.15     # fraction of cards that truly forget much faster than modeled
    target_retention = 0.9
    samples: list[dict] = []
    n_heldout = max(1, round(reviews_per * heldout_frac))

    for _ in range(n_cards):
        model_stability = rng.uniform(2.0, 30.0)   # model's belief about this card's S (days)
        est_error = math.exp(rng.gauss(0.0, sigma))  # multiplicative misestimate
        leech_penalty = 0.33 if rng.random() < leech_frac else 1.0
        true_stability = model_stability * est_error * leech_penalty

        for r in range(reviews_per):
            # The scheduler targets 0.9, but real reviews land OFF-SCHEDULE: users review
            # early (R high) or late (R low), and occasionally after a long gap. That spread
            # is exactly what makes a reliability diagram meaningful — otherwise every review
            # sits at predicted=0.9. lateness = actual_delay / scheduled_interval.
            scheduled = _interval_for_retention(model_stability, target_retention)
            lateness = math.exp(rng.gauss(0.15, 0.9))
            if rng.random() < 0.12:            # forgot-about-it gap: a long overdue tail
                lateness *= rng.uniform(3.0, 8.0)
            days = max(0.1, scheduled * lateness)
            predicted = power_forgetting_curve(days, model_stability)   # what the model reports
            r_true = power_forgetting_curve(days, true_stability)       # ground-truth recall prob
            recalled = 1 if rng.random() < r_true else 0

            # score only the held-out tail; earlier reviews just advance state
            if r >= reviews_per - n_heldout:
                samples.append({"predicted": predicted, "outcome": recalled,
                                "stability": model_stability, "days": days})

            # SRS state update (both the model's belief and the truth move together):
            if recalled:
                model_stability *= 1.9
                true_stability *= 1.9
            else:
                model_stability = max(1.0, model_stability * 0.5)
                true_stability = max(0.6, true_stability * 0.5)
    return samples


# --- calibration metrics ------------------------------------------------------


def metrics(samples: list[dict]) -> dict:
    n = len(samples)
    eps = 1e-9
    brier = sum((s["predicted"] - s["outcome"]) ** 2 for s in samples) / n
    log_loss = -sum(
        s["outcome"] * math.log(max(s["predicted"], eps))
        + (1 - s["outcome"]) * math.log(max(1 - s["predicted"], eps))
        for s in samples
    ) / n

    # reliability table: N_BINS equal-width predicted-probability bins
    bins = []
    ece = 0.0
    for b in range(N_BINS):
        lo, hi = b / N_BINS, (b + 1) / N_BINS
        in_bin = [s for s in samples if (lo <= s["predicted"] < hi) or (b == N_BINS - 1 and s["predicted"] == 1.0)]
        if in_bin:
            mean_pred = sum(s["predicted"] for s in in_bin) / len(in_bin)
            obs = sum(s["outcome"] for s in in_bin) / len(in_bin)
            ece += (len(in_bin) / n) * abs(mean_pred - obs)
        else:
            mean_pred = (lo + hi) / 2
            obs = None
        bins.append({"lo": round(lo, 2), "hi": round(hi, 2), "count": len(in_bin),
                     "mean_predicted": round(mean_pred, 4),
                     "observed": None if obs is None else round(obs, 4)})

    base_rate = sum(s["outcome"] for s in samples) / n
    # Mastery decision accuracy at the shipped 0.9 threshold (predicted-mastered vs recalled).
    tp = sum(1 for s in samples if s["predicted"] >= MASTERED_THRESHOLD and s["outcome"] == 1)
    fp = sum(1 for s in samples if s["predicted"] >= MASTERED_THRESHOLD and s["outcome"] == 0)
    mastered_pred = tp + fp
    mastery_precision = tp / mastered_pred if mastered_pred else None

    return {
        "n_heldout": n, "brier": round(brier, 4), "log_loss": round(log_loss, 4),
        "ece": round(ece, 4), "base_recall_rate": round(base_rate, 4),
        "mastery_threshold": MASTERED_THRESHOLD,
        "mastery_precision_at_threshold": None if mastery_precision is None else round(mastery_precision, 4),
        "bins": bins,
    }


# --- reliability diagram (self-contained SVG; Observatory dark) ---------------


def write_svg(m: dict, path: str) -> None:
    W = H = 420
    pad = 50
    plot = W - 2 * pad
    bg, grid, ink, diag, cyan, amber = "#07080d", "#1c2230", "#eaf0ff", "#3a4257", "#4ce0ff", "#f5b14c"

    def x(p): return pad + p * plot
    def y(p): return H - pad - p * plot

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{bg}"/>',
        f'<text x="{W/2}" y="24" fill="{ink}" font-family="system-ui,sans-serif" font-size="15" '
        f'text-anchor="middle">Memory-model calibration (held-out)</text>',
    ]
    for g in range(0, 11, 2):  # gridlines
        gp = g / 10
        parts.append(f'<line x1="{x(gp):.1f}" y1="{y(0):.1f}" x2="{x(gp):.1f}" y2="{y(1):.1f}" stroke="{grid}" stroke-width="1"/>')
        parts.append(f'<line x1="{x(0):.1f}" y1="{y(gp):.1f}" x2="{x(1):.1f}" y2="{y(gp):.1f}" stroke="{grid}" stroke-width="1"/>')
        parts.append(f'<text x="{x(gp):.1f}" y="{y(0)+16:.1f}" fill="{grid}" font-family="system-ui" font-size="9" text-anchor="middle">{gp:.1f}</text>')
        parts.append(f'<text x="{x(0)-8:.1f}" y="{y(gp)+3:.1f}" fill="{grid}" font-family="system-ui" font-size="9" text-anchor="end">{gp:.1f}</text>')
    # perfect-calibration diagonal
    parts.append(f'<line x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}" stroke="{diag}" stroke-width="1.5" stroke-dasharray="4 4"/>')
    # observed-vs-predicted polyline + points
    pts = [(b["mean_predicted"], b["observed"]) for b in m["bins"] if b["observed"] is not None]
    if len(pts) >= 2:
        poly = " ".join(f"{x(p):.1f},{y(o):.1f}" for p, o in pts)
        parts.append(f'<polyline points="{poly}" fill="none" stroke="{cyan}" stroke-width="2"/>')
    for p, o in pts:
        parts.append(f'<circle cx="{x(p):.1f}" cy="{y(o):.1f}" r="3.5" fill="{cyan}"/>')
    parts += [
        f'<text x="{W/2}" y="{H-10}" fill="{ink}" font-family="system-ui" font-size="11" text-anchor="middle">predicted recall</text>',
        f'<text x="14" y="{H/2}" fill="{ink}" font-family="system-ui" font-size="11" text-anchor="middle" transform="rotate(-90 14 {H/2})">observed recall</text>',
        f'<text x="{pad+6}" y="{pad+14}" fill="{amber}" font-family="system-ui" font-size="11">'
        f'Brier {m["brier"]:.3f} · log-loss {m["log_loss"]:.3f} · ECE {m["ece"]:.3f}</text>',
        "</svg>",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


# --- report -------------------------------------------------------------------


def print_report(m: dict) -> bool:
    print("\n" + "=" * 70 + "\nMEMORY MODEL — held-out calibration\n" + "=" * 70)
    print(f"  held-out reviews scored .... {m['n_heldout']}")
    print(f"  base recall rate ........... {m['base_recall_rate']:.1%}")
    print(f"  Brier score ................ {m['brier']:.4f}   (target <= {TARGETS['brier_max']}; lower better)")
    print(f"  log-loss ................... {m['log_loss']:.4f}   (target <= {TARGETS['log_loss_max']})")
    print(f"  ECE (calibration error) .... {m['ece']:.4f}   (target <= {TARGETS['ece_max']})")
    if m["mastery_precision_at_threshold"] is not None:
        print(f"  precision @ R>={m['mastery_threshold']} mastery  {m['mastery_precision_at_threshold']:.1%}  "
              f"(of cards called 'mastered', fraction actually recalled)")
    print("\n  reliability table (predicted-bin -> observed recall):")
    print("    bin            n     mean_pred   observed   gap")
    for b in m["bins"]:
        if b["observed"] is None:
            print(f"    [{b['lo']:.1f},{b['hi']:.1f})   {b['count']:>4}      {b['mean_predicted']:.3f}       —")
        else:
            gap = b["mean_predicted"] - b["observed"]
            flag = "  <-- overconfident" if gap > 0.10 else ("  <-- underconfident" if gap < -0.10 else "")
            print(f"    [{b['lo']:.1f},{b['hi']:.1f})   {b['count']:>4}      {b['mean_predicted']:.3f}      {b['observed']:.3f}    {gap:+.3f}{flag}")
    passed = (m["brier"] <= TARGETS["brier_max"] and m["log_loss"] <= TARGETS["log_loss_max"]
              and m["ece"] <= TARGETS["ece_max"])
    print(f"\n  --> calibration targets {'MET' if passed else 'NOT MET (reported as a negative result)'}")
    print()
    return passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", type=int, default=1500, help="simulated cards")
    ap.add_argument("--reviews-per", type=int, default=6, help="reviews per card")
    ap.add_argument("--heldout-frac", type=float, default=0.2, help="fraction of each card's last reviews held out")
    ap.add_argument("--seed", type=int, default=1729, help="RNG seed (reproducible)")
    ap.add_argument("--strict", action="store_true", help="exit non-zero if calibration targets are not met")
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--svg", default=OUT_SVG)
    args = ap.parse_args()

    _assert_engine_parity()
    rng = random.Random(args.seed)
    samples = simulate(rng, args.cards, args.reviews_per, args.heldout_frac)
    m = metrics(samples)
    m["config"] = {"cards": args.cards, "reviews_per": args.reviews_per,
                   "heldout_frac": args.heldout_frac, "seed": args.seed,
                   "decay": FSRS5_DEFAULT_DECAY, "engine_parity_verified": True}
    m["targets"] = TARGETS

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    write_svg(m, args.svg)
    print("engine-curve parity: OK (matches fsrs-5.2.0 test vectors)")
    print(f"wrote {os.path.relpath(args.out, REPO)} + {os.path.relpath(args.svg, REPO)}")

    ok = print_report(m)
    if args.strict and not ok:
        print("CALIBRATION GATE: targets not met.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
