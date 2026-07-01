# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Canonical Physics-GRE topic taxonomy.

Single source of truth for the PGRE subject list, exam content weights, tag
names, and official subscore grouping. The Rust engine change (SPECS.md S2,
``rslib/src/speedrun/``) mirrors these values; keep the two in sync.

Weights are the ETS-standard content split (PRD.md §2). The Brainlift firmly
cites Classical Mechanics 20%, Electromagnetism 18%, Quantum Mechanics 12%;
the remainder follow ETS's published outline and should be re-verified against
the ETS fact sheet before final use.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Anki tag namespace for all PGRE subject tags, e.g. ``pgre::classical_mechanics``.
TAG_PREFIX = "pgre"

#: A subject counts as "high weight" (its absence forces the dashboard to
#: abstain, SPECS.md S2-T08) when its exam weight is at least this fraction.
HIGH_WEIGHT_THRESHOLD = 0.10


@dataclass(frozen=True)
class Subject:
    """One PGRE content area."""

    key: str
    """Tag suffix / stable identifier, e.g. ``classical_mechanics``."""
    name: str
    """Human-readable label, e.g. ``Classical Mechanics``."""
    weight: float
    """Exam content weight in ``[0, 1]``; all weights sum to 1.0."""
    subscore: str
    """Official ETS subscore bucket this subject rolls up into."""

    @property
    def tag(self) -> str:
        """The Anki tag for this subject, e.g. ``pgre::classical_mechanics``."""
        return f"{TAG_PREFIX}::{self.key}"

    @property
    def is_high_weight(self) -> bool:
        return self.weight >= HIGH_WEIGHT_THRESHOLD


# Official ETS subscore buckets (PRD.md §2).
SUBSCORE_CLASSICAL = "classical_mechanics"
SUBSCORE_EM = "electromagnetism"
SUBSCORE_QUANTUM_ATOMIC = "quantum_atomic"

SUBJECTS: tuple[Subject, ...] = (
    Subject("classical_mechanics", "Classical Mechanics", 0.20, SUBSCORE_CLASSICAL),
    Subject("electromagnetism", "Electromagnetism", 0.18, SUBSCORE_EM),
    Subject("quantum_mechanics", "Quantum Mechanics", 0.12, SUBSCORE_QUANTUM_ATOMIC),
    Subject("atomic_physics", "Atomic Physics", 0.10, SUBSCORE_QUANTUM_ATOMIC),
    Subject(
        "thermo_stat_mech",
        "Thermodynamics & Statistical Mechanics",
        0.10,
        SUBSCORE_CLASSICAL,
    ),
    Subject("optics_waves", "Optics & Waves", 0.09, SUBSCORE_CLASSICAL),
    Subject("specialized_topics", "Specialized Topics", 0.09, SUBSCORE_QUANTUM_ATOMIC),
    Subject("special_relativity", "Special Relativity", 0.06, SUBSCORE_CLASSICAL),
    Subject("lab_methods", "Laboratory Methods", 0.06, SUBSCORE_CLASSICAL),
)

#: Lookup by stable key.
BY_KEY: dict[str, Subject] = {s.key: s for s in SUBJECTS}


def tag_for(key: str) -> str:
    """Return the canonical Anki tag for a subject key."""
    return BY_KEY[key].tag


def deck_name_for(key: str, root: str = "PGRE") -> str:
    """Return the nested deck name for a subject, e.g. ``PGRE::Classical Mechanics``."""
    return f"{root}::{BY_KEY[key].name}"


def total_weight() -> float:
    return sum(s.weight for s in SUBJECTS)


def validate() -> None:
    """Fail loudly if the taxonomy is internally inconsistent."""
    assert len({s.key for s in SUBJECTS}) == len(SUBJECTS), "duplicate subject keys"
    total = total_weight()
    assert abs(total - 1.0) < 1e-9, f"weights must sum to 1.0, got {total}"


# Validate at import so a bad edit is caught immediately.
validate()
