# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun PGRE: fork-local tooling built on top of Anki's Python API.

This package holds project-specific tooling for the Speedrun Physics-GRE build
(see PRD.md / SPECS.md at the repo root). It deliberately depends only on the
public ``anki`` library so it stays decoupled from engine internals, and its
generated artifacts are written under ``out/speedrun/`` (git-ignored), keeping
the tracked tree clean.
"""
