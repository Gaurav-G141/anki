# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""S1 test harness: verify the generated PGRE fixtures (SPECS.md S1-T01..T04).

Opens each fixture produced by ``make_fixtures.py`` and checks:

* S1-T01 - every note carries exactly one ``pgre::<subject>`` tag.
* S1-T02 - the main fixture covers all 9 subjects; the missing-high-weight
  fixture omits Classical Mechanics (a >=10% subject) on purpose.
* S1-T03 - the collection passes ``fix_integrity`` (dbcheck clean) and the
  exported ``.colpkg`` is a valid, non-empty archive.

Emits a structured JSON report (SPECS.md §E) and exits non-zero on any failure,
so it doubles as a re-runnable gate. Run via ``just speedrun-test``.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from anki.collection import Collection

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from speedrun import taxonomy  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out" / "speedrun"
SUBJECT_TAGS = {s.tag for s in taxonomy.SUBJECTS}


def _subject_tags_on_note(tags: list[str]) -> list[str]:
    return [t for t in tags if t in SUBJECT_TAGS]


def _result(test_id: str, status: str, metric: dict, note: str = "") -> dict:
    return {"test_id": test_id, "status": status, "metric": metric, "note": note}


def verify_fixture(entry: dict) -> list[dict]:
    name = entry["name"]
    anki2 = REPO_ROOT / entry["anki2"]
    colpkg = REPO_ROOT / entry["colpkg"]
    results: list[dict] = []
    is_empty = name == "pgre_empty"

    col = Collection(str(anki2))
    try:
        # S1-T01: exactly one subject tag per note.
        bad = 0
        for nid in col.find_notes(""):
            n = col.get_note(nid)
            if len(_subject_tags_on_note(n.tags)) != 1:
                bad += 1
        # Empty fixture has no notes -> vacuously fine.
        results.append(
            _result(
                f"S1-T01[{name}]",
                "PASS" if bad == 0 else "FAIL",
                {"name": "notes_without_exactly_one_subject_tag", "value": bad, "threshold": 0, "comparator": "=="},
            )
        )

        # S1-T02: subject coverage expectations.
        present = {
            s.key for s in taxonomy.SUBJECTS if col.find_notes(f'"tag:{s.tag}"')
        }
        if name == "pgre_main":
            missing = sorted({s.key for s in taxonomy.SUBJECTS} - present)
            results.append(
                _result(
                    f"S1-T02[{name}]",
                    "PASS" if not missing else "FAIL",
                    {"name": "subjects_present", "value": len(present), "threshold": len(taxonomy.SUBJECTS), "comparator": ">="},
                    note=f"missing={missing}" if missing else "all 9 subjects present",
                )
            )
        elif name == "pgre_missing_highweight":
            cm_absent = "classical_mechanics" not in present
            results.append(
                _result(
                    f"S1-T02[{name}]",
                    "PASS" if cm_absent else "FAIL",
                    {"name": "classical_mechanics_absent", "value": int(cm_absent), "threshold": 1, "comparator": "=="},
                    note="high-weight subject correctly absent (drives S2 abstain test)",
                )
            )

        # S1-T03a: integrity (dbcheck).
        _msg, ok = col.fix_integrity()
        results.append(
            _result(
                f"S1-T03a[{name}]",
                "PASS" if ok else "FAIL",
                {"name": "fix_integrity_ok", "value": int(ok), "threshold": 1, "comparator": "=="},
            )
        )
    finally:
        col.close()

    # S1-T03b: .colpkg is a valid, non-empty zip archive.
    valid_zip = colpkg.exists() and zipfile.is_zipfile(colpkg) and colpkg.stat().st_size > 0
    entries = len(zipfile.ZipFile(colpkg).namelist()) if valid_zip else 0
    results.append(
        _result(
            f"S1-T03b[{name}]",
            "PASS" if valid_zip and entries > 0 else "FAIL",
            {"name": "colpkg_zip_entries", "value": entries, "threshold": 1, "comparator": ">="},
        )
    )
    return results


def main() -> int:
    manifest_path = OUT_DIR / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: no fixtures found - run `just speedrun-fixtures` first.", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())

    all_results: list[dict] = []
    for entry in manifest["fixtures"]:
        all_results.extend(verify_fixture(entry))

    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")
    report = {
        "spec": "S1",
        "passed": passed,
        "failed": failed,
        "gate": "GREEN" if failed == 0 else "RED",
        "results": all_results,
    }
    print(json.dumps(report, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
