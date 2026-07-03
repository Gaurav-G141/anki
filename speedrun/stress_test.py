# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Stress + speed test the shared rslib engine on a large deck.

Times every hot path the desktop and iOS apps rely on (they share this engine —
iOS calls it over the C-FFI) and checks them against the PRD performance targets:
first load p95 < 1s, refresh < 500ms (spec'd to 50k cards; this runs at whatever
the deck holds — the bundled target is ~205k, ~4x the spec). Also stress-tests
the two-way sync path at full scale (full upload/download + incremental) when the
`anki-sync-server` binary is available.

Run via `just stress` (optionally `just stress deck=/path/to.apkg`).
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import statistics
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "out/pylib"))

import anki.lang  # noqa: E402
from anki import import_export_pb2, sync_pb2  # noqa: E402
from anki.collection import Collection  # noqa: E402

anki.lang.set_lang("en")

TARGET_FIRST_MS = 1000  # PRD: first load p95 < 1s
TARGET_REFRESH_MS = 500  # PRD: refresh < 500ms

R = sync_pb2.SyncCollectionResponse
PORT = 27732
ENDPOINT = f"http://127.0.0.1:{PORT}"

RESULTS: list[tuple[str, bool]] = []


def ms(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return (time.perf_counter() - t) * 1000, r


def stat(times):
    p95 = sorted(times)[min(len(times) - 1, int(round(0.95 * (len(times) - 1))))]
    return dict(
        n=len(times),
        min=min(times),
        med=statistics.median(times),
        p95=p95,
        max=max(times),
    )


def show(label, s, target=None):
    line = f"  {label:<34} n={s['n']:<3} med={s['med']:8.1f}ms  p95={s['p95']:8.1f}ms  max={s['max']:8.1f}ms"
    if target:
        ok = s["p95"] <= target
        line += f"   [{'PASS' if ok else 'FAIL'} <= {target}ms]"
        RESULTS.append((label, ok))
    print(line)


def check(label, ok, extra=""):
    RESULTS.append((label, ok))
    print(
        f"    [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {extra}" if extra else "")
    )


def hr(t):
    print("\n" + "=" * 90 + f"\n{t}\n" + "=" * 90)


# --- self-hosted sync server (best-effort) --------------------------------
class SyncServer:
    def __init__(self, base):
        self.base = base
        self.proc = None
        self.bin = self._find_bin()

    @staticmethod
    def _find_bin():
        for p in ("target/release/anki-sync-server", "target/debug/anki-sync-server"):
            full = os.path.join(REPO, p)
            if os.path.exists(full):
                return full
        return None

    def up(self):
        return socket.socket().connect_ex(("127.0.0.1", PORT)) == 0

    def start(self):
        if self.up():
            return True
        if not self.bin:
            return False
        shutil.rmtree(self.base, ignore_errors=True)
        os.makedirs(self.base, exist_ok=True)
        env = dict(
            os.environ,
            SYNC_HOST="127.0.0.1",
            SYNC_PORT=str(PORT),
            SYNC_BASE=self.base,
            SYNC_USER1="u1:p1",
            RUST_LOG="error",
        )
        self.proc = subprocess.Popen(
            [self.bin], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for _ in range(100):
            if self.up():
                return True
            time.sleep(0.1)
        return False

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None


def full_sync(col, auth, upload):
    out = col.sync_collection(auth, False)
    col.close_for_full_sync()
    col.full_upload_or_download(
        auth=auth, server_usn=out.server_media_usn, upload=upload
    )
    col.reopen(after_full_sync=True)


def review_batch(col, cids, ease=3):
    done = 0
    for cid in cids:
        card = col.get_card(cid)
        card.start_timer()
        try:
            col.sched.answerCard(card, ease)
            done += 1
        except Exception:
            pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--deck", required=True, help="path to a large .apkg to stress test"
    )
    ap.add_argument(
        "--reviews",
        type=int,
        default=20000,
        help="cards to review to populate FSRS state (default 20000)",
    )
    ap.add_argument(
        "--full-state",
        action="store_true",
        help="review EVERY card (worst case for the dashboard); slow",
    )
    ap.add_argument("--work", default=os.path.join(REPO, "out/speedrun/stress"))
    args = ap.parse_args()

    if not os.path.exists(args.deck):
        sys.exit(
            f"deck not found: {args.deck}\nPass one with:  just stress deck=/path/to/large.apkg"
        )

    work = args.work
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    colp = os.path.join(work, "big.anki2")

    hr("PHASE A — import + open the deck")
    col = Collection(colp)
    t_imp, _ = ms(
        lambda: col.import_anki_package(
            import_export_pb2.ImportAnkiPackageRequest(package_path=args.deck)
        )
    )
    ncards, nnotes = col.card_count(), col.note_count()
    print(
        f"  import .apkg ..................... {t_imp / 1000:8.1f}s   ({ncards} cards, {nnotes} notes)"
    )
    col.close()
    t_open, col = ms(Collection, colp)
    print(f"  cold open collection ............. {t_open:8.1f}ms")

    hr(
        f"PHASE B — home-screen hot paths @ {ncards} cards (target: first<{TARGET_FIRST_MS}ms, refresh<{TARGET_REFRESH_MS}ms)"
    )
    tree = [ms(col.sched.deck_due_tree)[0] for _ in range(12)]
    print(
        f"  deck tree FIRST load ............. {tree[0]:8.1f}ms   [{'PASS' if tree[0] <= TARGET_FIRST_MS else 'FAIL'} <= {TARGET_FIRST_MS}ms]"
    )
    RESULTS.append(("deck tree first load", tree[0] <= TARGET_FIRST_MS))
    show("deck tree refresh", stat(tree[1:]), TARGET_REFRESH_MS)
    show(
        "find_cards('') full scan", stat([ms(col.find_cards, "")[0] for _ in range(8)])
    )
    some = col.find_cards("")[:200]

    def render():
        for cid in some:
            c = col.get_card(cid)
            c.question()
            c.answer()

    show("render 200 cards (Q+A)", stat([ms(render)[0] for _ in range(5)]))

    hr(
        "PHASE C — FSRS memory-state, then the Memory dashboard (THE p95<1s / refresh<500ms target)"
    )
    col.set_config("fsrs", True)
    pool = col.find_cards("is:new")
    batch = pool if args.full_state else pool[: args.reviews]
    print(f"  answering {len(batch)} cards to populate FSRS state + revlog ...")
    t0 = time.perf_counter()
    done = review_batch(col, batch)
    el = time.perf_counter() - t0
    print(
        f"  answered {done} in {el:6.1f}s  ->  {done / max(el, 1e-9):8.0f} cards/sec  ({el * 1000 / max(done, 1):.2f} ms/card)"
    )
    print(f"  revlog rows now: {col.db.scalar('select count(*) from revlog')}")

    def mastery():
        return col._backend.topic_mastery(
            mastered_threshold=0.9, review_floor=20, coverage_floor=0.40
        )

    t_first, resp = ms(mastery)
    print(
        f"  Memory dashboard FIRST load ...... {t_first:8.1f}ms   [{'PASS' if t_first <= TARGET_FIRST_MS else 'FAIL'} <= {TARGET_FIRST_MS}ms]"
        f"   (score={getattr(resp, 'memory_score', 0):.3f})"
    )
    RESULTS.append(("memory dashboard first load", t_first <= TARGET_FIRST_MS))
    show(
        "Memory dashboard refresh",
        stat([ms(mastery)[0] for _ in range(12)]),
        TARGET_REFRESH_MS,
    )
    show(
        "deck_mastery refresh",
        stat(
            [
                ms(lambda: col._backend.deck_mastery(mastered_threshold=0.9))[0]
                for _ in range(12)
            ]
        ),
        TARGET_REFRESH_MS,
    )

    hr("PHASE D — SYNC at full scale (the path both apps use)")
    server = SyncServer(os.path.join(work, "syncbase"))
    if not server.start():
        print("  SKIPPED — anki-sync-server binary not found.")
        print("  Build it to include this phase:  cargo build -p anki-sync-server")
    else:
        try:
            auth = col.sync_login("u1", "p1", ENDPOINT)
            auth.endpoint = ENDPOINT
            t_up, _ = ms(lambda: full_sync(col, auth, True))
            print(
                f"  FULL UPLOAD  mac->server ......... {t_up / 1000:8.1f}s   ({ncards} cards)"
            )
            iosp = os.path.join(work, "ios.anki2")
            ios = Collection(iosp)
            t_dl, _ = ms(lambda: full_sync(ios, auth, False))
            print(
                f"  FULL DOWNLOAD server->ios ........ {t_dl / 1000:8.1f}s   (ios cards={ios.card_count()})"
            )
            check(
                "full download adopted all cards",
                ios.card_count() == ncards,
                f"{ios.card_count()}/{ncards}",
            )
            n = review_batch(col, col.find_cards("is:new")[:50])
            t_iu, _ = ms(lambda: col.sync_collection(auth, False))
            t_id, _ = ms(lambda: ios.sync_collection(auth, False))
            print(f"  incremental push ({n} reviews) ..... {t_iu:8.1f}ms")
            print(f"  incremental pull to ios .......... {t_id:8.1f}ms")
            check(
                "incremental sync propagates",
                ios.db.scalar("select count(*) from revlog") >= done + n,
            )
            ios.close()
        finally:
            server.stop()

    hr("SUMMARY vs REQUIREMENTS (PRD: first load p95<1s, refresh<500ms; spec 50k)")
    nfail = sum(1 for _, ok in RESULTS if not ok)
    for label, ok in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    print(
        f"\n  {len(RESULTS) - nfail}/{len(RESULTS)} checks pass  (deck: {ncards} cards)"
    )
    col.close()
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
