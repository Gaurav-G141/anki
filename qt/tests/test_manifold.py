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

from types import SimpleNamespace

import anki.lang
from aqt.dialog_reuse import should_reuse_dialog

# Importing aqt.manifold evaluates class-level translated strings (its bottom-bar
# labels), which needs the legacy global `tr` bound to a live i18n backend.
# set_lang() creates and retains that backend, so do it before the import.
anki.lang.set_lang("en")

from aqt.manifold import Manifold  # noqa: E402


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


def _stub_manifold(state: str, col: object = object()) -> Manifold:
    """A Manifold with the Qt-heavy __init__ bypassed, wired just enough to
    exercise ``_on_collection_changed`` (the sync/load refresh safety net)."""
    m = Manifold.__new__(Manifold)
    m._refresh_needed = False
    m.refreshed = 0

    def _count() -> None:
        m.refreshed += 1

    m.refresh = _count  # type: ignore[method-assign]
    m.mw = SimpleNamespace(state=state, col=col)
    return m


def test_sync_reshows_colours_when_on_manifold():
    # After a sync (which can rewrite intervals wholesale) the spikes must be
    # recomputed and reshown, even without a focus change — else they'd revert
    # to the pre-sync (e.g. all-red) colouring.
    m = _stub_manifold(state="manifold")
    m._on_collection_changed()
    assert m.refreshed == 1
    assert m._refresh_needed is True


def test_sync_only_marks_dirty_when_not_on_manifold():
    # Off-screen: don't repaint the wrong state, but mark dirty so show() (which
    # always rebuilds) picks up the new colours when the manifold is next opened.
    m = _stub_manifold(state="deckBrowser")
    m._on_collection_changed()
    assert m.refreshed == 0
    assert m._refresh_needed is True


def test_no_refresh_without_a_collection():
    # collection_did_load can fire around teardown/open with no live collection;
    # never try to render then.
    m = _stub_manifold(state="manifold", col=None)
    m._on_collection_changed()
    assert m.refreshed == 0
    assert m._refresh_needed is True


def _changes(**kw: bool) -> SimpleNamespace:
    fields = {"card": False, "deck": False, "study_queues": False}
    fields.update(kw)
    return SimpleNamespace(**fields)


def test_op_executed_refreshes_on_card_interval_change():
    # A reschedule / interval edit changes a card's maturity (and thus the spike
    # colour), so op_executed must recompute — even though it isn't a deck change.
    m = _stub_manifold(state="manifold")
    dirty = m.op_executed(_changes(card=True), handler=None, focused=True)
    assert m.refreshed == 1
    assert dirty is True


def test_op_executed_refreshes_on_review_answer():
    # Answering a review card moves its interval; study_queues flags that.
    m = _stub_manifold(state="manifold")
    m.op_executed(_changes(study_queues=True), handler=None, focused=True)
    assert m.refreshed == 1


def test_op_executed_defers_when_not_focused():
    # Off-screen change: mark dirty, repaint later (on focus / re-entry).
    m = _stub_manifold(state="manifold")
    dirty = m.op_executed(_changes(card=True), handler=None, focused=False)
    assert m.refreshed == 0
    assert dirty is True


def test_op_executed_ignores_own_changes():
    # A change this screen itself made shouldn't trigger a self-refresh loop.
    m = _stub_manifold(state="manifold")
    m.op_executed(_changes(card=True, deck=True), handler=m, focused=True)
    assert m.refreshed == 0
    assert m._refresh_needed is False
