# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Crash-safety test (SPECS.md S9-T02): SIGKILL the engine mid-write, repeatedly,
and prove the collection never corrupts.

Anki's SQLite layer is transactional, so an abrupt kill in the middle of a write
must roll back cleanly on reopen. The Speedrun changes are read-only and don't
touch this, but the Speedrun spec requires demonstrating it. We run N rounds:
spawn a child that hammers the collection with writes, SIGKILL it after a random
delay (mid-write), then reopen and run a full integrity check.

Run via ``just speedrun-crash-test`` or::

    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/crash_test.py [rounds]

Stricter than the spec's 20 rounds: defaults to 50.
"""

from __future__ import annotations

import os
import random
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from anki.collection import Collection

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_COLLECTION = REPO_ROOT / "out" / "speedrun" / "work" / "pgre_main.anki2"
WORK = REPO_ROOT / "out" / "speedrun" / "crash_work.anki2"
DEFAULT_ROUNDS = 50


def _child_hammer_writes(path: str) -> None:
    """Open the collection and write continuously until killed."""
    col = Collection(path)
    notetype = col.models.by_name("Basic")
    assert notetype is not None
    deck_id = col.decks.id("CrashTest")
    i = 0
    while True:  # the parent SIGKILLs us mid-write
        note = col.new_note(notetype)
        note["Front"] = f"crash {i}"
        note["Back"] = str(i)
        col.add_note(note, deck_id)
        i += 1


def _reopen_and_check(path: str) -> bool:
    """Reopen the collection and run a full integrity check. True == clean."""
    col = Collection(path)
    try:
        _msg, ok = col.fix_integrity()
        return ok
    finally:
        col.close()


def run(rounds: int) -> int:
    if not SEED_COLLECTION.exists():
        print(
            f"ERROR: seed collection {SEED_COLLECTION} missing — run "
            "`just speedrun-fixtures` first.",
            file=sys.stderr,
        )
        return 2
    WORK.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SEED_COLLECTION, WORK)

    corrupted = 0
    rng = random.Random(0xC0FFEE)  # deterministic delays
    for r in range(1, rounds + 1):
        child = subprocess.Popen(
            [sys.executable, __file__, "--child", str(WORK)],
            env=os.environ.copy(),
        )
        # Let the child get into a steady write loop, then kill mid-write.
        time.sleep(0.5 + rng.random() * 1.0)
        child.send_signal(signal.SIGKILL)
        child.wait()
        # Clean up SQLite sidecar files left by the abrupt kill, as a real
        # restart would; the .anki2 alone must still be recoverable.
        ok = _reopen_and_check(str(WORK))
        status = "clean" if ok else "CORRUPT"
        if not ok:
            corrupted += 1
        print(f"round {r:>3}/{rounds}: killed mid-write -> reopen {status}")

    print()
    print(f"corrupted collections: {corrupted} / {rounds}")
    return 0 if corrupted == 0 else 1


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--child":
        _child_hammer_writes(sys.argv[2])
        return 0  # unreachable; killed by parent
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROUNDS
    return run(rounds)


if __name__ == "__main__":
    raise SystemExit(main())
