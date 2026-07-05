# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Memory dashboard (Physics GRE fork).

Surfaces the honest per-topic memory score from the Rust ``SpeedrunService``
``TopicMastery`` RPC: a mastered-fraction estimate with a Wilson 95% range, or
an abstaining "No score yet" when the give-up rule fires (too few graded reviews
or too little subject coverage). The score UI is the SvelteKit page
``speedrun-dashboard``.

That page fetches its data over the POST-RPC bridge, which the mediasrv only
permits from an **API-enabled** webview. The main window's webview is *not*
API-enabled (the reviewer runs with a restricted endpoint whitelist), so — like
the Stats window — the dashboard lives in its own dialog with an AnkiWebView of
kind ``SPEEDRUN_DASHBOARD`` (added to the API-access allowlist in ``webview.py``).
"""

from __future__ import annotations

import aqt
from aqt.qt import QDialog, Qt, QVBoxLayout
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind


class MemoryDashboard(QDialog):
    """A window hosting the ``speedrun-dashboard`` page in an API-enabled webview."""

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "memoryDashboard"
        self.setWindowTitle("Ankimatter — Scores")
        disable_help_button(self)
        self.setMinimumSize(600, 500)
        restoreGeom(self, self.name, default_size=(840, 760))

        self.web = AnkiWebView(kind=AnkiWebViewKind.SPEEDRUN_DASHBOARD)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)

        self.web.load_sveltekit_page("speedrun-dashboard")
        self.show()
        self.activateWindow()

    def reject(self) -> None:
        if self.web:
            self.web.cleanup()
            self.web = None  # type: ignore[assignment]
        saveGeom(self, self.name)
        QDialog.reject(self)
