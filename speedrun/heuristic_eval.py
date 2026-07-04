# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Stage-1 eval for the Physics-GRE Heuristic Coach.

Uses GPT-4o to produce a validated *optimal-approach answer key* for real released
PGRE problems, and scores its quality against pre-declared gates:

  * ANSWER CORRECTNESS = 100% by construction — the correct letter comes from the
    scraped key and is asserted (deterministic code gate); a record whose model
    output disagrees is regenerated once, then dropped. Answer-match is NOT a
    quality metric (a trivial MCQ machine gets 100%).
  * equal-or-better than the community solution (LLM judge)   [beat-the-baseline]
  * zero hallucinated eliminations (LLM + rule verifier)
  * student_explanation is clear/warm (LLM + length rule)     [human-facing quality]
  * strict-JSON, no malformed output

Splits GR9277 (the only set with answer choices) into a DEV split (tune prompts)
and a HELD-OUT split (report final numbers; never used while tuning).

The OpenAI key is read from `.env` (OPENAI_API_KEY=...) at the repo root, or the
real env var. Nothing here touches app code. Run:  python speedrun/heuristic_eval.py --help
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "speedrun"))

import heuristic_prompts as P  # noqa: E402
from pgre_problems import load_gr9277_with_choices  # noqa: E402

DATA_DIR = os.path.join(REPO, "speedrun", "data")
OUT_PATH = os.path.join(DATA_DIR, "optimal_approaches.jsonl")
DEFAULT_MODEL = "gpt-4o"
DEV_MAX_NUM = 45  # GR9277 problems with num <= 45 -> dev split; rest -> held-out

# Pre-declared quality cutoffs (answer correctness is a separate hard 100% gate).
CUTOFFS = {
    "equal_or_better_min": 0.90,
    "hallucinated_eliminations_max": 0,
    "student_clarity_min": 0.90,
    "malformed_json_max": 0,
}


# --- .env + OpenAI plumbing ---------------------------------------------------


def load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# Accept the standard name plus common aliases (the user's .env uses OPEN_AI_API).
KEY_ALIASES = ["OPENAI_API_KEY", "OPEN_AI_API", "OPENAI_KEY", "OPENAI_APIKEY"]


def get_key() -> str:
    load_dotenv(os.path.join(REPO, ".env"))
    for name in KEY_ALIASES:
        key = os.environ.get(name, "").strip()
        if key:
            return key
    sys.exit(
        f"No OpenAI key found. Set one of {KEY_ALIASES} in a .env file at the repo root "
        "(gitignored) or export it, then re-run. (Use --dry-run to test offline.)"
    )


class OpenAIClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.calls = 0

    def chat_json(self, messages, temperature=0.2, max_retries=2, timeout=60) -> dict:
        """Call chat.completions in JSON mode; return the parsed dict.
        Never logs the key or full headers on error."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        last = ""
        for attempt in range(max_retries + 1):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=timeout)
                self.calls += 1
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    return json.loads(content)
                last = f"HTTP {r.status_code}: {r.text[:160]}"
                if r.status_code in (429, 500, 502, 503, 529) and attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
            except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
                last = f"{type(e).__name__}: {str(e)[:160]}"
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
        raise RuntimeError(f"OpenAI call failed ({last})")


# --- per-problem evaluation ---------------------------------------------------


def eval_problem(client: OpenAIClient, prob) -> dict:
    """Generate + validate one optimal-approach record. Returns a result dict with
    the record and per-check outcomes."""
    res = {"id": prob.id, "subject": prob.subject_key, "answer": prob.answer}

    # 1) generate; deterministic answer gate (regenerate once on mismatch)
    rec = None
    for _ in range(2):
        try:
            out = client.chat_json(P.build_optimal_prompt(prob))
        except (RuntimeError,) as e:
            res["error"] = str(e)
            res["malformed_json"] = True
            return res
        if not isinstance(out, dict) or "final_answer" not in out:
            res["malformed_json"] = True
            continue
        if str(out.get("final_answer", "")).strip().upper() == prob.answer.upper():
            rec = out
            break
    if rec is None:
        res["answer_gate_failed"] = True  # never emit a wrong-answer record
        return res
    res["malformed_json"] = False
    res["record"] = rec

    # 2) equal-or-better than the scraped solution (baseline the coach must beat)
    try:
        judge = client.chat_json(P.build_judge_prompt(prob, rec.get("expert_reasoning", "")))
        res["verdict"] = judge.get("verdict")
        res["equal_or_better"] = judge.get("verdict") in ("better", "equal") and bool(
            judge.get("b_is_correct", True)
        )
    except RuntimeError as e:
        res["verdict"], res["equal_or_better"] = f"judge_error:{e}", False

    # 3) elimination verifier = a FILTER (assignment §7f: block bad content, don't
    #    just flag it). We strip any elimination that (a) names the correct answer
    #    (deterministic) or (b) the checker flags as invalid, so the SHIPPED record
    #    only ever contains verified eliminations. We separately track the raw
    #    (pre-filter) defect rate as the generator-quality signal.
    def up(e):
        return str(e.get("choice", "")).strip().upper()

    elims = rec.get("eliminations", []) or []
    removed = [e for e in elims if up(e) == prob.answer.upper()]  # correct answer never eliminated
    res["answer_in_eliminations"] = bool(removed)
    elims = [e for e in elims if up(e) != prob.answer.upper()]

    raw_valid = not res["answer_in_eliminations"]
    if elims:
        try:
            chk = client.chat_json(P.build_elimination_check_prompt(prob, elims))
            if not chk.get("all_valid", False):
                raw_valid = False
                bad_choices = {str(b.get("choice", "")).strip().upper() for b in (chk.get("bad") or [])}
                removed += [e for e in elims if up(e) in bad_choices]
                elims = [e for e in elims if up(e) not in bad_choices]
        except RuntimeError:
            raw_valid = False  # checker unavailable -> drop all eliminations (fail safe)
            removed += elims
            elims = []
    rec["eliminations"] = elims  # shipped: verified-only
    res["raw_eliminations_valid"] = raw_valid
    res["removed_eliminations"] = removed
    res["shipped_bad_eliminations"] = 0  # by construction

    # 4) student-explanation clarity/tone
    expl = rec.get("student_explanation", "")
    words = len(expl.split())
    try:
        cl = client.chat_json(P.build_clarity_prompt(prob, expl))
        res["student_clear"] = bool(cl.get("clear", False)) and words <= 140
        res["clarity_issues"] = cl.get("issues", [])
    except RuntimeError as e:
        res["student_clear"], res["clarity_issues"] = False, [f"clarity_error:{e}"]
    res["explanation_words"] = words
    return res


# --- reporting ---------------------------------------------------------------


def summarize(results: list[dict], label: str) -> dict:
    n = len(results)
    emitted = [r for r in results if "record" in r]
    m = len(emitted) or 1
    gate_fail = sum(1 for r in results if r.get("answer_gate_failed"))
    malformed = sum(1 for r in results if r.get("malformed_json"))
    eob = sum(1 for r in emitted if r.get("equal_or_better"))
    clear = sum(1 for r in emitted if r.get("student_clear"))
    pre_flagged = sum(1 for r in emitted if not r.get("raw_eliminations_valid", True))
    removed = sum(len(r.get("removed_eliminations", [])) for r in emitted)
    shipped_bad = sum(r.get("shipped_bad_eliminations", 0) for r in emitted)
    return {
        "split": label, "n": n, "emitted": len(emitted),
        "answer_gate_failed": gate_fail, "malformed_json": malformed,
        "eob": eob, "clear": clear, "pre_flagged": pre_flagged,
        "removed": removed, "shipped_bad": shipped_bad,
        "_eob_frac": eob / m, "_clear_frac": clear / m,
    }


def print_report(summaries: list[dict]) -> bool:
    """Print the per-split report; return True iff EVERY split met its cutoffs.
    Callers should treat a False return as a hard gate (do not ship)."""
    all_passed = True
    print("\n" + "=" * 70 + "\nHEURISTIC COACH — Stage 1 eval\n" + "=" * 70)
    for s in summaries:
        m = s["emitted"] or 1
        print(f"\n[{s['split']}]  n={s['n']}  emitted={s['emitted']}")
        print(f"  answer correctness ......... {s['emitted']}/{s['n']} = "
              f"{100*s['emitted']/max(s['n'],1):.0f}%  (deterministic, hard gate)")
        print(f"  answer-gate rejects ........ {s['answer_gate_failed']}")
        print(f"  malformed JSON ............. {s['malformed_json']}")
        print(f"  equal-or-better vs scraped . {s['eob']}/{s['emitted']} = {s['eob']/m:.0%}  [beats the community baseline]")
        print(f"  student-explanation clear .. {s['clear']}/{s['emitted']} = {s['clear']/m:.0%}")
        print(f"  eliminations flagged (raw) . {s['pre_flagged']} record(s); "
              f"{s['removed']} elimination(s) removed by verifier")
        print(f"  bad eliminations SHIPPED ... {s['shipped_bad']}  (verifier filters them out)")
        passed = (
            s["_eob_frac"] >= CUTOFFS["equal_or_better_min"]
            and s["shipped_bad"] <= CUTOFFS["hallucinated_eliminations_max"]
            and s["_clear_frac"] >= CUTOFFS["student_clarity_min"]
            and s["malformed_json"] <= CUTOFFS["malformed_json_max"]
        )
        all_passed = all_passed and passed
        print(f"  --> cutoff {'PASS' if passed else 'NOT MET'} "
              f"(eob>={CUTOFFS['equal_or_better_min']:.0%}, shipped-bad=0, "
              f"clear>={CUTOFFS['student_clarity_min']:.0%}, malformed=0)")
    print()
    return all_passed


# --- main --------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "held", "all"], default="dev")
    ap.add_argument("--limit", type=int, default=0, help="cap problems (0 = no cap); for cheap smoke runs")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="no API calls; validate prompts/parsing offline")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    problems = load_gr9277_with_choices()
    dev = [p for p in problems if p.num <= DEV_MAX_NUM]
    held = [p for p in problems if p.num > DEV_MAX_NUM]
    chosen = {"dev": dev, "held": held, "all": problems}[args.split]
    if args.limit:
        chosen = chosen[: args.limit]

    print(f"primary set: {len(problems)} (dev {len(dev)} / held {len(held)}); "
          f"running split='{args.split}' on {len(chosen)} problems; model={args.model}")

    if args.dry_run:
        # Offline validation: build every prompt, confirm they render, show one.
        for p in chosen:
            _ = P.build_optimal_prompt(p)
            _ = P.build_judge_prompt(p, "x")
            _ = P.build_elimination_check_prompt(p, [{"choice": "A", "reason": "x"}])
            _ = P.build_clarity_prompt(p, "x")
        sample = P.build_optimal_prompt(chosen[0])
        print(f"\n[dry-run] built prompts for {len(chosen)} problems OK. Sample user prompt "
              f"({chosen[0].id}), first 900 chars:\n{'-'*60}\n{sample[1]['content'][:900]}\n{'-'*60}")
        print("[dry-run] no API calls made. Add OPENAI_API_KEY to .env and drop --dry-run to run for real.")
        return

    client = OpenAIClient(get_key(), args.model)
    os.makedirs(DATA_DIR, exist_ok=True)

    results = []
    for i, p in enumerate(chosen, 1):
        r = eval_problem(client, p)
        results.append(r)
        flag = "OK" if "record" in r else ("GATE-FAIL" if r.get("answer_gate_failed") else "ERR")
        print(f"  [{i}/{len(chosen)}] {p.id:10} {flag:9} "
              f"eob={r.get('verdict','-'):6} clear={r.get('student_clear','-')} "
              f"elim_ok={r.get('eliminations_valid','-')}")

    # write only validated (answer-gated) records
    with open(args.out, "w", encoding="utf-8") as f:
        for r in results:
            if "record" in r:
                rec = dict(r["record"])
                rec["id"] = r["id"]
                rec["subject"] = r["subject"]
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    emitted = sum(1 for r in results if "record" in r)
    print(f"\nwrote {emitted} validated approaches -> {args.out}   (OpenAI calls: {client.calls})")

    if args.split == "all":
        dev_ids = {p.id for p in dev}
        dev_res = [r for r in results if r["id"] in dev_ids]
        held_res = [r for r in results if r["id"] not in dev_ids]
        ok = print_report([summarize(dev_res, "dev (tuning)"), summarize(held_res, "held-out (frozen)")])
    else:
        ok = print_report([summarize(results, args.split)])
    if not ok:
        print("EVAL GATE: held-out cutoffs NOT met — the bank must not ship.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
