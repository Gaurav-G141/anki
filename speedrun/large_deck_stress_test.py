# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Large-deck stress harness: does a very large deck break the app?

Imports a big ``.apkg`` (default: a ~200k-card deck) into a THROWAWAY collection
and exercises every path a huge collection could stress:

  S1 import               S5 TopicMastery RPC (dashboard) at scale
  S2 integrity check      S6 Speed Recall config-store scaling  <-- key risk
  S3 reopen time          S7 crash-safety mid-write on the big deck
  S4 search/browse        S8 peak memory (RSS)

Never touches the user's real collection (works in a temp dir). Prints a staged
report + writes JSON to out/speedrun/large_deck_stress_result.json. Exit code is
nonzero if any check fails (integrity, corruption, exception, or a perf blow-up).

Usage:
  PYTHONPATH=qt:out/qt:out/pylib out/pyenv/bin/python \\
      speedrun/large_deck_stress_test.py [path/to/deck.apkg]
"""
from __future__ import annotations

import json
import os
import random
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from anki.collection import Collection, ImportAnkiPackageRequest

DEFAULT_DECK = "/Users/gaurav/Downloads/Cities_of_Your_Country.apkg"
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "out" / "speedrun"
# Make the in-repo ``speedrun`` package importable regardless of cwd (the S5
# stage does ``from speedrun import taxonomy``).
sys.path.insert(0, str(REPO))

# Perf budgets (generous — this is "does it break", not the 50k p95 gate).
BUDGET = {
    "import_s": 600.0,       # importing ~200k should finish well under 10 min
    "reopen_s": 5.0,         # cold open of a huge collection
    "mastery_p95_s": 3.0,    # dashboard RPC at 200k (50k target is <1s)
    "search_all_s": 5.0,
}


def rss_mb() -> float:
    # macOS: ru_maxrss is bytes; Linux: kilobytes.
    m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return m / (1024 * 1024) if sys.platform == "darwin" else m / 1024


def timed(fn):
    t = time.perf_counter()
    val = fn()
    return val, time.perf_counter() - t


def _crash_child(path: str) -> None:
    col = Collection(path)
    nt = col.models.by_name("Basic")
    did = col.decks.id("CrashStress")
    i = 0
    while True:  # parent SIGKILLs mid-write
        note = col.new_note(nt)
        note["Front"] = f"x{i}"; note["Back"] = str(i)
        col.add_note(note, did)
        i += 1


def run(deck: str) -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--crash-child":
        _crash_child(sys.argv[2]); return 0

    report: dict = {"deck": deck, "stages": {}, "failures": []}

    def fail(msg: str) -> None:
        report["failures"].append(msg)
        print(f"  !! FAIL: {msg}")

    if not os.path.exists(deck):
        print(f"deck not found: {deck}"); return 2
    report["deck_size_mb"] = round(os.path.getsize(deck) / 1e6, 1)

    workdir = tempfile.mkdtemp(prefix="bigdeck_")
    colpath = os.path.join(workdir, "c.anki2")
    print(f"deck: {deck} ({report['deck_size_mb']} MB)\nwork: {colpath}\n")

    # --- S1 import ---
    print("S1 import…")
    col = Collection(colpath)
    try:
        _, t = timed(lambda: col.import_anki_package(
            ImportAnkiPackageRequest(package_path=deck)))
        notes, cards = col.note_count(), col.card_count()
        report["stages"]["import"] = {"seconds": round(t, 1), "notes": notes, "cards": cards}
        print(f"   imported {notes:,} notes / {cards:,} cards in {t:.1f}s")
        if t > BUDGET["import_s"]:
            fail(f"import too slow: {t:.0f}s > {BUDGET['import_s']}s")
        if notes == 0:
            fail("import produced 0 notes")
    except Exception as e:
        fail(f"import raised {type(e).__name__}: {e}"); col.close(); return _finish(report)

    # --- S2 integrity ---
    print("S2 integrity (fix_integrity)…")
    (_msg, ok), t = timed(col.fix_integrity)
    report["stages"]["integrity"] = {"seconds": round(t, 1), "clean": bool(ok)}
    print(f"   clean={ok} in {t:.1f}s")
    if not ok:
        fail("integrity check not clean after import")

    # --- S4 search/browse (S3 reopen done after) ---
    print("S4 search/browse…")
    (allc, t1) = timed(lambda: col.find_cards(""))
    (alln, t2) = timed(lambda: col.find_notes(""))
    report["stages"]["search"] = {
        "find_cards_all_s": round(t1, 2), "n_cards": len(allc),
        "find_notes_all_s": round(t2, 2)}
    print(f"   find_cards all: {len(allc):,} in {t1:.2f}s ; find_notes all in {t2:.2f}s")
    if t1 > BUDGET["search_all_s"]:
        fail(f"find_cards too slow: {t1:.1f}s")

    # --- S5 TopicMastery at scale ---
    print("S5 TopicMastery RPC (untagged, then PGRE-tagged at scale)…")
    try:
        # untagged: must not crash; should abstain
        r0, t0 = timed(lambda: col.speedrun.topic_mastery())
        report["stages"]["mastery_untagged"] = {"seconds": round(t0, 3), "abstain": r0.abstain}
        print(f"   untagged: abstain={r0.abstain} in {t0*1000:.0f}ms")
        # tag ALL notes round-robin across 9 pgre subjects, then measure p50/p95
        from speedrun import taxonomy
        nids = list(col.find_notes(""))
        subjects = list(taxonomy.SUBJECTS)
        _, ttag = timed(lambda: [
            col.tags.bulk_add(nids[i::len(subjects)], subjects[i].tag)
            for i in range(len(subjects))])
        report["stages"]["bulk_tag"] = {"seconds": round(ttag, 1), "notes": len(nids)}
        print(f"   bulk-tagged {len(nids):,} notes across 9 subjects in {ttag:.1f}s")
        times = []
        for _ in range(5):
            _, tt = timed(lambda: col.speedrun.topic_mastery())
            times.append(tt)
        times.sort()
        p50, p95 = times[len(times)//2], times[-1]
        r1 = col.speedrun.topic_mastery()
        report["stages"]["mastery_tagged"] = {
            "p50_ms": round(p50*1000), "p95_ms": round(p95*1000),
            "coverage": round(r1.coverage, 3), "abstain": r1.abstain,
            "total_reviews": r1.total_reviews}
        print(f"   tagged: p50={p50*1000:.0f}ms p95={p95*1000:.0f}ms coverage={r1.coverage:.2f}")
        if p95 > BUDGET["mastery_p95_s"]:
            fail(f"mastery p95 too slow at {len(nids):,} cards: {p95*1000:.0f}ms")
    except Exception as e:
        fail(f"mastery RPC raised {type(e).__name__}: {e}")

    # --- S6 Speed Recall config-store scaling (the key risk) ---
    print("S6 Speed Recall schedule-store scaling…")
    try:
        from aqt import speedrecall as sr
        cids = list(col.find_cards(""))[:12000]
        rng = random.Random(0)
        batch = 2000
        trend = []
        now = 1000.0
        for start in range(0, len(cids), batch):
            chunk = cids[start:start+batch]
            _, tb = timed(lambda: [sr.record_answer(col, c, rng.randint(1, 4),
                                                     rng.random()*90, now=now) for c in chunk])
            size = len(json.dumps(col.get_config(sr.SCHED_KEY, {})))
            trend.append({"total": start+len(chunk), "batch_s": round(tb, 2),
                          "cfg_bytes": size})
            print(f"   after {start+len(chunk):>6,} recorded: batch={tb:.2f}s cfg={size/1e6:.1f}MB")
        _, tdue = timed(lambda: sr.due_card_ids(col, now=now + 10**9))
        report["stages"]["speedrecall_store"] = {"trend": trend, "due_scan_s": round(tdue, 2)}
        # O(n^2) detector: last batch should not be dramatically slower than first
        if len(trend) >= 2 and trend[-1]["batch_s"] > 8 * max(trend[0]["batch_s"], 0.05):
            fail(f"Speed Recall store scales super-linearly: batch grew "
                 f"{trend[0]['batch_s']:.2f}s -> {trend[-1]['batch_s']:.2f}s (O(n^2) JSON rewrite)")
    except Exception as e:
        fail(f"speedrecall store test raised {type(e).__name__}: {e}")

    report["peak_rss_mb"] = round(rss_mb())
    print(f"S8 peak RSS so far: {report['peak_rss_mb']} MB")
    col.close()

    # --- S3 reopen (cold) ---
    print("S3 reopen (cold open of the big collection)…")
    c2, t = timed(lambda: Collection(colpath))
    report["stages"]["reopen"] = {"seconds": round(t, 2)}
    print(f"   reopened in {t:.2f}s")
    if t > BUDGET["reopen_s"]:
        fail(f"reopen too slow: {t:.1f}s")
    c2.close()

    # --- S7 crash safety on the big deck ---
    print("S7 crash-safety mid-write x5 on the big collection…")
    crashwork = os.path.join(workdir, "crash.anki2")
    corrupted = 0
    for r in range(1, 6):
        shutil.copy(colpath, crashwork)
        child = subprocess.Popen([sys.executable, __file__, "--crash-child", crashwork],
                                 env=os.environ.copy())
        time.sleep(1.0 + r * 0.3)
        child.send_signal(signal.SIGKILL); child.wait()
        cc = Collection(crashwork)
        _m, ok = cc.fix_integrity(); cc.close()
        if not ok:
            corrupted += 1
        print(f"   round {r}/5: reopen {'clean' if ok else 'CORRUPT'}")
    report["stages"]["crash"] = {"rounds": 5, "corrupted": corrupted}
    if corrupted:
        fail(f"{corrupted}/5 corrupted after mid-write crash on the big deck")

    return _finish(report)


def _finish(report: dict) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "large_deck_stress_result.json").write_text(json.dumps(report, indent=2))
    print("\n==== SUMMARY ====")
    print(json.dumps(report["stages"], indent=2))
    if report["failures"]:
        print(f"\nRESULT: {len(report['failures'])} FAILURE(S):")
        for f in report["failures"]:
            print("  -", f)
        return 1
    print("\nRESULT: PASS — the large deck did not break any tested path.")
    return 0


if __name__ == "__main__":
    deck = sys.argv[2] if (len(sys.argv) >= 3 and sys.argv[1] == "--crash-child") else (
        sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DECK)
    raise SystemExit(run(deck))
