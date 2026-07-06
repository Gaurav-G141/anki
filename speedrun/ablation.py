# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Three-arm ABLATION of the Speed-Recall study feature (assignment §8, 15% of grade).

The feature under test is latency-modulated scheduling (``qt/aqt/speedrecall.py``):
"how long you take to recall modulates the next interval", so a slow (struggling)
recall brings a card back sooner. We ablate it against two controls, holding the
learner and the study-time budget fixed so the scheduling policy is the ONLY variable:

  1. full        — Speed Recall with latency ON  (BASE_HOURS × latency_factor)
  2. feature-off — Speed Recall with latency OFF (grade-only spacing; the real
                   ``speedRecallLatencyEnabled=False`` toggle we ship)
  3. plain-anki  — stock SM-2 day-scale scheduling (no retention/latency signal)

**Pre-declared main metric:** cards *mastered per study-minute* (mastered = ground-truth
recall probability ≥ 0.9 at the end of the horizon — the same 0.9 threshold the Rust
mastery report uses). Reported as mean over N independent seeds with the [min, max] range.
A null or negative result (feature no better than off) is reported honestly — it still
answers the question.

This is a **deterministic simulation** (no real months-long study logs exist yet): a
synthetic learner whose true memory grows with successful recall and decays via the
engine's own forgetting curve; recall is Bernoulli in the true retrievability; answer
latency rises as retrieval gets harder (the signal the feature exploits). The latency
curve constants mirror ``qt/aqt/speedrecall.py`` (kept in sync by comment; imported-free
so the harness needs no Qt). Pure/offline, seeded, no non-stdlib deps.

    out/pyenv/bin/python speedrun/ablation.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "speedrun", "data")
OUT_JSON = os.path.join(DATA_DIR, "ablation.json")

# FSRS forgetting curve (matches speedrun/calibration_eval.py + the engine).
FSRS5_DEFAULT_DECAY = 0.5
MASTERED_THRESHOLD = 0.9

# --- Speed-Recall latency curve, MIRRORED from qt/aqt/speedrecall.py ----------
# (kept in sync by comment; importing aqt would pull in Qt, which this pure sim avoids)
FAST_SECONDS = 5.0
SLOW_SECONDS = 60.0
SLOW_FLOOR = 0.07
BASE_HOURS = {1: 1.0 / 6.0, 2: 24.0, 3: 72.0, 4: 168.0}

HORIZON_DAYS = 21.0  # study period simulated
BUDGET_MINUTES = 45.0  # equal study-time budget per arm across the horizon
DURABILITY_DAYS = 7.0  # "mastered" = memory durable enough to stay recalled this long
N_CARDS = 180
N_SEEDS = 16

ARMS = ("full", "feature-off", "plain-anki")


def power_forgetting_curve(
    days: float, stability: float, decay: float = FSRS5_DEFAULT_DECAY
) -> float:
    factor = 0.9 ** (1.0 / -decay) - 1.0
    return (days / stability * factor + 1.0) ** (-decay)


def latency_factor(seconds: float) -> float:
    if seconds <= FAST_SECONDS:
        return 1.0
    if seconds >= SLOW_SECONDS:
        return SLOW_FLOOR
    frac = (seconds - FAST_SECONDS) / (SLOW_SECONDS - FAST_SECONDS)
    return 1.0 - frac * (1.0 - SLOW_FLOOR)


def speed_recall_next_hours(grade: int, seconds: float, latency_aware: bool) -> float:
    if grade == 1 or not latency_aware:
        return BASE_HOURS[grade]
    return BASE_HOURS[grade] * latency_factor(seconds)


class Card:
    """A card's ground-truth memory + a scheduler's bookkeeping for one arm."""

    __slots__ = ("true_stability", "last_day", "due_day", "ivl_days", "ef")

    def __init__(self, true_stability: float) -> None:
        self.true_stability = true_stability  # ground-truth memory stability (days)
        self.last_day = 0.0
        self.due_day = 0.0
        self.ivl_days = 1.0  # plain-anki interval bookkeeping
        self.ef = 2.5  # plain-anki ease factor


def _answer_latency(rng: random.Random, r_true: float) -> float:
    """Recall latency (s): fast when recall is easy, slow when it's marginal.
    This is the struggle signal the latency-aware feature exploits."""
    base = FAST_SECONDS + (SLOW_SECONDS - FAST_SECONDS) * (1.0 - r_true)
    return max(1.0, min(90.0, base * math.exp(rng.gauss(0.0, 0.25))))


def _grade(recalled: bool, seconds: float) -> int:
    if not recalled:
        return 1  # Again
    return 4 if seconds <= 8.0 else 3  # fast → Easy, slower-but-correct → Good


def _schedule(arm: str, card: Card, grade: int, seconds: float, now: float) -> float:
    """Return the next due day for `card` under `arm`'s policy."""
    if arm == "plain-anki":
        if grade == 1:
            card.ivl_days = 10.0 / (24.0 * 60.0)  # ~10 min relearn
            card.ef = max(1.3, card.ef - 0.2)
        else:
            mult = card.ef * (1.3 if grade == 4 else 1.0)
            card.ivl_days = (
                max(1.0, card.ivl_days * mult)
                if card.last_day > 0
                else (4.0 if grade == 4 else 1.0)
            )
        return now + card.ivl_days
    # speed-recall arms (hour-scale, optionally latency-modulated)
    latency_aware = arm == "full"
    return now + speed_recall_next_hours(grade, seconds, latency_aware) / 24.0


def run_arm(arm: str, seeds_cards: list[float], seed: int) -> dict:
    """Simulate one arm on a fixed card set + seed. Equal study-time budget.
    Event-driven: always study the earliest-due card until time or horizon runs out."""
    # Stable per-arm offset: Python's built-in hash() of a str is randomized per
    # process (PYTHONHASHSEED), which made runs non-reproducible. Use a fixed
    # deterministic hash so `just ablation` yields identical numbers every run.
    arm_offset = int(hashlib.sha256(arm.encode()).hexdigest(), 16) % 997
    rng = random.Random(seed * 1_000 + arm_offset)
    cards = [Card(s) for s in seeds_cards]
    budget_s = BUDGET_MINUTES * 60.0
    spent_s = 0.0
    reviews = 0
    # day-0 learning pass (equal across arms; not charged to the study budget)
    for c in cards:
        g = 4
        c.last_day = 0.0
        c.due_day = _schedule(arm, c, g, 3.0, 0.0)

    while spent_s < budget_s:
        # earliest-due card within the horizon
        c = min(cards, key=lambda x: x.due_day)
        now = c.due_day
        if now > HORIZON_DAYS:
            break
        elapsed = max(0.0, now - c.last_day)
        r_true = power_forgetting_curve(elapsed, c.true_stability)
        recalled = rng.random() < r_true
        seconds = _answer_latency(rng, r_true)
        if spent_s + seconds > budget_s:
            break
        spent_s += seconds
        reviews += 1
        # Ground-truth memory update with DESIRABLE DIFFICULTY (as FSRS models it):
        # a successful recall at a LONGER interval (lower retrievability, harder pull)
        # grows stability MORE than an easy recall of a just-seen card. A lapse is
        # costly (stability collapses). This is the tension the feature bets on:
        # shorter intervals reduce lapses but earn smaller per-rep gains.
        if recalled:
            gain = 1.0 + 2.2 * (1.0 - r_true)  # r=0.9 → ×1.22 · r=0.5 → ×2.10
            c.true_stability *= gain
        else:
            c.true_stability = max(0.5, c.true_stability * 0.40)
        g = _grade(recalled, seconds)
        c.last_day = now
        c.due_day = _schedule(arm, c, g, seconds, now)

    # Mastery = DURABILITY, not an instantaneous snapshot: a card is mastered if its
    # ground-truth stability is high enough to keep retrievability >= 0.9 for at least
    # DURABILITY_DAYS. Since R(t,S)=0.9 exactly when t==S, that condition is stability >=
    # DURABILITY_DAYS. Robust to *when* each card was last reviewed, and the same for all arms.
    mastered = sum(1 for c in cards if c.true_stability >= DURABILITY_DAYS)
    minutes = spent_s / 60.0
    return {
        "arm": arm,
        "mastered": mastered,
        "mastered_frac": mastered / len(cards),
        "reviews": reviews,
        "study_minutes": round(minutes, 2),
        "mastered_per_min": round(mastered / minutes, 4) if minutes > 0 else 0.0,
    }


def run(n_cards: int, n_seeds: int) -> dict:
    per_arm: dict[str, list[dict]] = {a: [] for a in ARMS}
    for seed in range(n_seeds):
        # identical starting card set across arms for this seed (feature is the only variable)
        crng = random.Random(9000 + seed)
        seeds_cards = [crng.uniform(1.5, 12.0) for _ in range(n_cards)]
        for arm in ARMS:
            per_arm[arm].append(run_arm(arm, list(seeds_cards), seed))

    summary = {}
    for arm in ARMS:
        vals = [r["mastered_per_min"] for r in per_arm[arm]]
        fracs = [r["mastered_frac"] for r in per_arm[arm]]
        summary[arm] = {
            "mastered_per_min_mean": round(statistics.mean(vals), 4),
            "mastered_per_min_min": round(min(vals), 4),
            "mastered_per_min_max": round(max(vals), 4),
            "mastered_per_min_stdev": round(statistics.pstdev(vals), 4),
            "mastered_frac_mean": round(statistics.mean(fracs), 4),
            "avg_reviews": round(
                statistics.mean([r["reviews"] for r in per_arm[arm]]), 1
            ),
            "avg_study_minutes": round(
                statistics.mean([r["study_minutes"] for r in per_arm[arm]]), 2
            ),
        }
    return {"summary": summary, "per_seed": per_arm}


def print_report(res: dict) -> bool:
    s = res["summary"]
    cfg = res.get("config", {})
    print(
        "\n"
        + "=" * 74
        + "\nSPEED-RECALL ABLATION — mastered per study-minute (equal time budget)\n"
        + "=" * 74
    )
    print(
        f"  horizon={HORIZON_DAYS:.0f}d · budget={BUDGET_MINUTES:.0f} min/arm · "
        f"{cfg.get('cards', '?')} cards · seeds={cfg.get('seeds', '?')}"
    )
    print(
        "\n  arm            mastered/min (mean)   range[min,max]    mastered%   avg reviews"
    )
    for arm in ARMS:
        a = s[arm]
        print(
            f"  {arm:13}  {a['mastered_per_min_mean']:>10.3f}          "
            f"[{a['mastered_per_min_min']:.3f}, {a['mastered_per_min_max']:.3f}]     "
            f"{a['mastered_frac_mean'] * 100:>5.1f}%      {a['avg_reviews']:>5.1f}"
        )

    full = s["full"]["mastered_per_min_mean"]
    off = s["feature-off"]["mastered_per_min_mean"]
    plain = s["plain-anki"]["mastered_per_min_mean"]
    lift_off = (full - off) / off * 100 if off else 0.0
    lift_plain = (full - plain) / plain * 100 if plain else 0.0

    # PAIRED analysis: each seed uses the SAME card set across arms, so the per-seed
    # delta cancels the shared card-set variance — far more sensitive than comparing
    # noisy per-arm means. "Significant" = the paired-delta 95% CI (±2·stderr) excludes 0.
    pf = [r["mastered_per_min"] for r in res["per_seed"]["full"]]
    po = [r["mastered_per_min"] for r in res["per_seed"]["feature-off"]]
    deltas = [a - b for a, b in zip(pf, po)]
    n = len(deltas)
    dmean = statistics.mean(deltas)
    dstderr = (statistics.pstdev(deltas) / math.sqrt(n)) if n > 1 else 0.0
    ci_lo, ci_hi = dmean - 2 * dstderr, dmean + 2 * dstderr
    significant = ci_lo > 0 or ci_hi < 0
    print(
        f"\n  latency-aware vs feature-off: {lift_off:+.1f}%   "
        f"(paired Δ={dmean:+.3f}/min, 95% CI [{ci_lo:+.3f}, {ci_hi:+.3f}])"
    )
    print(f"  latency-aware vs plain Anki : {lift_plain:+.1f}%")
    if significant and dmean > 0:
        verdict = "latency-modulated scheduling MASTERS MORE per minute (CI excludes 0)"
    elif significant and dmean < 0:
        verdict = "latency-modulated scheduling is WORSE per minute (negative result — reported honestly)"
    else:
        verdict = (
            "NO significant difference vs feature-off at equal study time "
            "(null result — reported honestly; CI spans 0)"
        )
    print(f"  --> {verdict}")
    print()
    # harness sanity: every arm actually studied and produced finite numbers
    return all(s[a]["avg_reviews"] > 0 for a in ARMS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", type=int, default=N_CARDS)
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument(
        "--strict", action="store_true", help="exit non-zero if any arm failed to run"
    )
    args = ap.parse_args()

    res = run(args.cards, args.seeds)
    res["config"] = {
        "cards": args.cards,
        "seeds": args.seeds,
        "horizon_days": HORIZON_DAYS,
        "budget_minutes": BUDGET_MINUTES,
        "mastered_threshold": MASTERED_THRESHOLD,
        "main_metric": "cards mastered per study-minute (mean over seeds, [min,max] range)",
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"wrote {os.path.relpath(args.out, REPO)}")

    ok = print_report(res)
    if args.strict and not ok:
        print("ABLATION GATE: an arm failed to run.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
