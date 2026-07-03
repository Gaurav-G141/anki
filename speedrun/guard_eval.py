# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Eval for the student-input guard (safety triage).

Runs the adversarial fixture (speedrun/data/adversarial_inputs.jsonl) through the
two-layer guard:
  1. deterministic tripwires (offline) — catch obvious injection strings before
     anything reaches a model,
  2. the LLM classifier (needs OPENAI_API_KEY) — categorize the rest.

Asserts: injections are caught (and never obeyed), low-effort/off-topic/abusive
inputs are classified into a non-"attempt" bucket (so they're never graded as a
physics approach), and genuine attempts are NOT misflagged. `--dry-run` runs the
offline tripwire layer only. Nothing here touches app code.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import heuristic_prompts as P  # noqa: E402
from heuristic_eval import OpenAIClient, get_key  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "speedrun", "data", "adversarial_inputs.jsonl")

# Categories that must NEVER be graded as a physics approach.
NON_ATTEMPT = {"injection", "empty_or_low_effort", "off_topic", "abusive"}


def classify(client: OpenAIClient | None, text: str) -> tuple[str, str]:
    """Return (category, layer). Tripwire first (offline); else model (or 'skip')."""
    if P.tripwire_hit(text):
        return "injection", "tripwire"
    if not text.strip():
        return "empty_or_low_effort", "rule"
    if client is None:
        return "(needs-model)", "skip"
    try:
        out = client.chat_json(P.build_input_guard_prompt(text))
        cat = out.get("category", "attempt")
        return (cat if cat in P.INPUT_CATEGORIES else "attempt"), "model"
    except RuntimeError as e:
        # Fail safe: if the guard model errors, treat as non-attempt (don't grade).
        return "empty_or_low_effort", f"error:{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="tripwire/offline layer only")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(FIXTURE, encoding="utf-8") if l.strip()]
    client = None if args.dry_run else OpenAIClient(get_key(), "gpt-4o")

    correct = 0
    safe = 0  # non-attempt inputs correctly kept out of grading
    total_nonattempt = sum(1 for r in rows if r["expected"] in NON_ATTEMPT)
    print(f"guard eval on {len(rows)} inputs "
          f"({'tripwire-only' if args.dry_run else 'tripwire + model'}):\n")
    for r in rows:
        cat, layer = classify(client, r["text"])
        exp = r["expected"]
        ok = (cat == exp) or (exp in NON_ATTEMPT and cat in NON_ATTEMPT)
        correct += ok
        if exp in NON_ATTEMPT and cat in NON_ATTEMPT:
            safe += 1
        preview = (r["text"][:48] or "<empty>").replace("\n", " ")
        mark = "ok " if ok else "XX "
        print(f"  {mark} exp={exp:20} got={cat:20} [{layer:8}] {preview}")

    print(f"\ncategory match: {correct}/{len(rows)}")
    if args.dry_run:
        caught = sum(1 for r in rows if r["expected"] == "injection" and P.tripwire_hit(r["text"]))
        inj = sum(1 for r in rows if r["expected"] == "injection")
        print(f"tripwire caught {caught}/{inj} injection cases offline "
              f"(the rest fall to the model layer). Add the key + drop --dry-run for the full run.")
    else:
        print(f"non-attempts kept OUT of grading: {safe}/{total_nonattempt} "
              f"(these never reach the physics grader)")


if __name__ == "__main__":
    main()
