# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Calabi-Yau manifold home screen (Physics GRE fork).

Replaces the deck list as the app's landing screen. The manifold image is shown
with a button at each of its outer points; clicking a point opens that subject
deck's study (overview) screen. The classic deck list stays one click away.

Structurally this mirrors ``aqt.deckbrowser.DeckBrowser`` (a webview screen
driven by ``pycmd`` bridge commands) so it slots into the main-window state
machine with no special-casing. The GUI-free bits (deck list, HTML) live in
``aqt.pgre`` and are unit-tested there.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import aqt
from anki.collection import OpChanges
from anki.decks import DeckId
from aqt import AnkiQt, gui_hooks
from aqt.operations.deck import add_deck_dialog, set_current_deck
from aqt.pgre import build_manifold_html
from aqt.sound import av_player
from aqt.toolbar import BottomBar
from aqt.utils import openLink, shortcut, tr


class ManifoldBottomBar:
    def __init__(self, manifold: Manifold) -> None:
        self.manifold = manifold


class Manifold:
    """The Calabi-Yau home screen."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web
        self.bottom = BottomBar(mw, mw.bottomWeb)
        self._refresh_needed = False
        #: Current pagination depth: depth n shows decks 9n..9n+8 on the spikes.
        self.depth = 0

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._linkHandler, self)
        self.mw.toolbar.redraw()
        # Everyone lands on depth 0; deeper pages are reached via "More decks".
        self.depth = 0
        self.refresh()

    def refresh(self) -> None:
        self.web.stdHtml(
            build_manifold_html(self.mw.col, self.depth),
            js=[
                "js/vendor/jquery.min.js",
                "js/mathjax.js",
                "js/vendor/mathjax/tex-chtml-full.js",
            ],
            context=self,
        )
        self._draw_buttons()
        self._refresh_needed = False
        gui_hooks.deck_browser_did_render(self.mw.deckBrowser)

    def refresh_if_needed(self) -> None:
        if self._refresh_needed:
            self.refresh()

    def op_executed(
        self, changes: OpChanges, handler: object | None, focused: bool
    ) -> bool:
        # A deck being added/removed changes which points are live, so refresh
        # on any deck/study-queue change originating elsewhere.
        if (changes.deck or changes.study_queues) and handler is not self:
            self._refresh_needed = True
        if focused:
            self.refresh_if_needed()
        return self._refresh_needed

    # Event handlers
    ##########################################################################

    def _linkHandler(self, url: str) -> Any:
        if ":" in url:
            (cmd, arg) = url.split(":", 1)
        else:
            cmd, arg = url, ""
        if cmd == "open":
            self._open_deck(DeckId(int(arg)))
        elif cmd == "more":
            self._show_more_decks()
        elif cmd == "classic":
            self.mw.moveToState("deckBrowser")
        elif cmd == "shared":
            openLink(f"{aqt.appShared}decks/")
        elif cmd == "create":
            self._on_create()
        elif cmd == "import":
            self.mw.onImport()
        elif cmd == "speedrecall":
            self.mw.moveToState("speedRecall")
        elif cmd == "memory":
            self._open_memory_dashboard()
        return False

    def _open_memory_dashboard(self) -> None:
        from aqt.memorydash import MemoryDashboard

        # Re-focus an existing window instead of stacking duplicates.
        existing = getattr(self.mw, "_memory_dashboard", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        setattr(self.mw, "_memory_dashboard", MemoryDashboard(self.mw))

    def _open_deck(self, deck_id: DeckId) -> None:
        set_current_deck(parent=self.mw, deck_id=deck_id).success(
            lambda _: self.mw.onOverview()
        ).run_in_background(initiator=self)

    def _show_more_decks(self) -> None:
        # Advance one page. build_manifold_html wraps the depth modulo the number
        # of pages, so from the last page this loops back to depth 0.
        self.depth += 1
        self.refresh()

    def _on_create(self) -> None:
        if op := add_deck_dialog(
            parent=self.mw, default_text=self.mw.col.decks.current()["name"]
        ):
            op.run_in_background()

    # Bottom bar (keeps the add/import features on the home screen)
    ##########################################################################

    drawLinks = [
        ["", "shared", tr.decks_get_shared()],
        ["", "create", tr.decks_create_deck()],
        ["Ctrl+Shift+I", "import", tr.decks_import_file()],
        ["Ctrl+Shift+R", "speedrecall", "⚡ Speed Recall"],
        ["Ctrl+Shift+M", "memory", "📊 Memory"],
    ]

    def _draw_buttons(self) -> None:
        buf = ""
        for keys, cmd, label in deepcopy(self.drawLinks):
            title = tr.actions_shortcut_key(val=shortcut(keys)) if keys else ""
            buf += (
                f"<button title='{title}' onclick='pycmd(\"{cmd}\");'>{label}</button>"
            )
        self.bottom.draw(
            buf=buf,
            link_handler=self._linkHandler,
            web_context=ManifoldBottomBar(self),
        )
