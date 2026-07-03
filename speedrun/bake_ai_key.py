# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Copy the OpenAI key from `.env` into the git-ignored bundled file that the
built desktop app reads (`qt/aqt/data/pgre_ai_key.txt`).

TESTING-ONLY convenience: the key becomes plaintext inside the packaged .app so
the Heuristic-Coach FRQ grader works without per-machine env setup. Use a
dedicated low-quota key and remove/rotate it before any distribution. Run via
`just bake-ai-key`.
"""

from __future__ import annotations

import pathlib

_ALIASES = ("OPENAI_API_KEY", "OPEN_AI_API", "OPENAI_KEY", "OPENAI_APIKEY")


def main() -> None:
    env = pathlib.Path(".env")
    kv: dict[str, str] = {}
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip().strip('"').strip("'")
    key = next((kv[n] for n in _ALIASES if kv.get(n)), "")
    if not key:
        raise SystemExit(
            "no OpenAI key found in .env (expected one of " + ", ".join(_ALIASES) + ")"
        )
    dest = pathlib.Path("qt/aqt/data/pgre_ai_key.txt")
    dest.write_text(key + "\n", encoding="utf-8")
    print(f"baked {dest} (key length {len(key)}) — rebuild to embed it in the app")


if __name__ == "__main__":
    main()
