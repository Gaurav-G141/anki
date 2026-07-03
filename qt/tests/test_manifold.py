# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Tests for the manifold home screen's singleton-dialog reuse guard.

Regression cover for the "Memory dashboard won't open a second time" bug: after
the dashboard is closed once, ``garbage_collect_on_dialog_finish`` calls
``deleteLater()`` on it, so the stored reference points at a deleted C++ object.
The old code called ``existing.isVisible()`` on that stale reference, which raises
``RuntimeError`` and left the dashboard unopenable. ``should_reuse_dialog`` must
treat a deleted (or missing) dialog as "not reusable" so a fresh one is created.

These exercise the pure guard with stubs, so no running Qt app is needed.
"""

from __future__ import annotations

from aqt.dialog_reuse import should_reuse_dialog


class _VisibleDialog:
    def isVisible(self) -> bool:
        return True


class _HiddenDialog:
    def isVisible(self) -> bool:
        return False


class _DeletedDialog:
    """Mimics a PyQt wrapper whose C++ object was deleted (via deleteLater)."""

    def isVisible(self) -> bool:
        raise RuntimeError(
            "wrapped C/C++ object of type MemoryDashboard has been deleted"
        )


def test_no_existing_dialog_is_not_reused():
    assert should_reuse_dialog(None) is False


def test_visible_dialog_is_reused():
    assert should_reuse_dialog(_VisibleDialog()) is True


def test_hidden_dialog_is_not_reused():
    # A closed-but-not-yet-deleted dialog: reports hidden, so open a fresh one.
    assert should_reuse_dialog(_HiddenDialog()) is False


def test_deleted_dialog_is_not_reused_instead_of_raising():
    # The actual bug: a stale reference to a deleted dialog must NOT raise, and
    # must report "not reusable" so the Memory dashboard reopens.
    assert should_reuse_dialog(_DeletedDialog()) is False
