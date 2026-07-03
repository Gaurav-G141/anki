# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Safe reuse of singleton dialogs across reopens.

A window we keep a single reference to (e.g. the Memory dashboard) is closed by
the user, at which point ``garbage_collect_on_dialog_finish`` calls
``deleteLater()`` on it. The Python wrapper then points at a deleted C++ object,
and *any* attribute access on it — including ``isVisible()`` — raises
``RuntimeError``. Callers use :func:`should_reuse_dialog` to decide whether the
stored reference is still a live, visible dialog to re-focus, or a dead/absent
one that should be replaced with a fresh instance.

Kept dependency-free (no Qt/i18n imports) so it is unit-testable headlessly.
"""

from __future__ import annotations

from typing import Any


def should_reuse_dialog(existing: Any) -> bool:
    """Return True only if ``existing`` is a live, visible dialog to re-focus.

    A ``None`` reference (never opened) or a deleted C++ object (closed earlier,
    now raising ``RuntimeError`` on access) both return False, so the caller
    creates a fresh dialog instead of crashing.
    """
    if existing is None:
        return False
    try:
        return bool(existing.isVisible())
    except RuntimeError:
        # Underlying C++ dialog was already deleted (deleteLater on close).
        return False
