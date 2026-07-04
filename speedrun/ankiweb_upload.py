# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Upload the seeded dummy collection to a (throwaway) AnkiWeb account.

Portable grader path: after this runs, a grader logs into the fork app (desktop or
iOS) with the throwaway AnkiWeb credentials, syncs, and gets the pre-seeded
progress (three confident scores) on any machine — no terminal, no ANKI_BASE.

Credentials are read from the environment (or repo-root ``.env``); they are NEVER
printed or committed. Expected vars:

    ANKIWEB_USER=you+pgre-dummy@example.com
    ANKIWEB_PASS=...

Usage (after `just build` + seeding a collection):

    # 1) seed a fresh collection
    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/seed_dummy_account.py \\
        --out out/speedrun/ankiweb_dummy/collection.anki2
    # 2) push it to AnkiWeb (force full upload, replacing that account's collection)
    PYTHONPATH=out/pylib out/pyenv/bin/python speedrun/ankiweb_upload.py \\
        --col out/speedrun/ankiweb_dummy/collection.anki2

WARNING: a FULL UPLOAD **replaces** whatever is in that AnkiWeb account. Only point
it at a dedicated throwaway account.
"""

from __future__ import annotations

import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "out/pylib"))

from anki.collection import Collection  # noqa: E402


def _load_dotenv() -> None:
    path = os.path.join(REPO, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _creds() -> tuple[str, str]:
    _load_dotenv()
    user = os.environ.get("ANKIWEB_USER", "").strip()
    pw = os.environ.get("ANKIWEB_PASS", "").strip()
    if not user or not pw:
        raise SystemExit(
            "Set ANKIWEB_USER and ANKIWEB_PASS (in the environment or repo-root .env) "
            "to a THROWAWAY AnkiWeb account. Nothing was uploaded."
        )
    return user, pw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--col", required=True, help="path to the seeded collection.anki2 to upload")
    ap.add_argument("--endpoint", default="",
                    help="custom sync endpoint; leave empty for AnkiWeb (field sent unset)")
    args = ap.parse_args()

    if not os.path.exists(args.col):
        raise SystemExit(f"collection not found: {args.col} (seed it first)")

    user, pw = _creds()
    col = Collection(args.col)
    try:
        # 1) authenticate (endpoint '' => AnkiWeb; returns auth with resolved shard)
        auth = col.sync_login(username=user, password=pw, endpoint=args.endpoint or None)
        print(f"logged in as {user!r}")
        # 2) a first sync_collection resolves the sharded host (new_endpoint). A full
        #    upload MUST target that endpoint; skipping this yields AnkiWeb's
        #    "400 missing original size". This reports FULL_SYNC (our collection vs the
        #    account's) but applies nothing — we then force the upload.
        out = col.sync_collection(auth, sync_media=False)
        if out.new_endpoint:
            auth.endpoint = out.new_endpoint
        # 3) force a FULL UPLOAD so this collection becomes the account's collection.
        #    Mirrors aqt/sync.py: close_for_full_sync() then full_upload_or_download(upload=True).
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth, server_usn=None, upload=True)
    except Exception as e:  # noqa: BLE001 — surface a clean message, never dump creds
        raise SystemExit(f"upload failed: {type(e).__name__}: {e}") from None

    print("\n✅ uploaded the dummy collection to AnkiWeb.")
    print("Graders: in the fork app, use a FRESH profile, Sync, log in with the")
    print("throwaway credentials, and accept the one-time full DOWNLOAD.")


if __name__ == "__main__":
    main()
