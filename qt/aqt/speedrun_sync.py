# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Convenience sync login/logout for the Speedrun fork (desktop).

Stock Anki logs in via the Sync button (an AnkiWeb-style prompt) and reads the
self-hosted server URL from Preferences. For testing iOS<->desktop sync against a
self-hosted ``anki-sync-server``, this adds one-step Tools-menu items: log in with
an explicit endpoint (username / password / server URL) — mirroring the iOS login
sheet — and log out. It reuses Anki's own machinery: ``Collection.sync_login``,
the profile's sync-auth storage, and ``aqt.sync.sync_collection``.
"""

from __future__ import annotations

import aqt
from anki.collection import Collection
from anki.sync_pb2 import SyncAuth
from aqt.operations import QueryOp
from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    qconnect,
)
from aqt.sync import sync_collection
from aqt.utils import disable_help_button, showInfo, tooltip


def _normalize_endpoint(raw: str) -> str:
    """Bare base URL Anki expects (it appends ``/sync/...`` itself). Fixes the
    common 404/"invalid server" mistakes: missing scheme, trailing slash, or an
    accidental ``/sync`` path. Empty ⇒ AnkiWeb (unchanged)."""
    s = raw.strip()
    if not s:
        return ""
    if "://" not in s:
        s = "http://" + s
    s = s.rstrip("/")
    for path in ("/sync", "/msync"):
        if s.endswith(path):
            s = s[: -len(path)]
    return s.rstrip("/")


def sync_login_dialog(mw: aqt.main.AnkiQt) -> None:
    """Prompt for username/password/endpoint, log in, then sync."""
    if not mw.col:
        return
    dialog = QDialog(mw)
    dialog.setWindowTitle("Sync — Log In")
    disable_help_button(dialog)
    layout = QFormLayout(dialog)

    saved_user = (mw.pm.profile or {}).get("syncUser") or ""
    username = QLineEdit(saved_user)
    password = QLineEdit()
    password.setEchoMode(QLineEdit.EchoMode.Password)
    endpoint = QLineEdit(mw.pm.custom_sync_url() or "http://127.0.0.1:8080")
    layout.addRow("Username", username)
    layout.addRow("Password", password)
    layout.addRow("Server URL", endpoint)
    hint = QLabel(
        "Leave the server URL blank to use AnkiWeb, or enter a self-hosted "
        "server's base URL, e.g. http://127.0.0.1:8080 (no /sync path)."
    )
    hint.setWordWrap(True)
    layout.addRow(hint)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    layout.addRow(buttons)
    qconnect(buttons.accepted, dialog.accept)
    qconnect(buttons.rejected, dialog.reject)

    if not dialog.exec():
        return
    user = username.text().strip()
    pw = password.text()
    endpoint_url = _normalize_endpoint(endpoint.text())
    if not user or not pw:
        showInfo("Please enter a username and password.", parent=mw)
        return
    _login(mw, user, pw, endpoint_url)


def _login(mw: aqt.main.AnkiQt, username: str, password: str, endpoint: str) -> None:
    def op(col: Collection) -> SyncAuth:
        return col.sync_login(
            username=username, password=password, endpoint=endpoint or None
        )

    def on_success(auth: SyncAuth) -> None:
        mw.pm.set_sync_key(auth.hkey)
        mw.pm.set_sync_username(username)
        mw.pm.set_custom_sync_url(endpoint or None)
        tooltip("Logged in — syncing…", parent=mw)
        # First sync bootstraps the shared collection (full upload/download, with
        # Anki's usual confirmation); later syncs are incremental two-way.
        sync_collection(mw, lambda: None)

    QueryOp(parent=mw, op=op, success=on_success).with_progress(
        "Logging in…"
    ).run_in_background()


def sync_logout(mw: aqt.main.AnkiQt) -> None:
    """Clear the stored sync credential (next sync will prompt to log in again)."""
    mw.pm.clear_sync_auth()
    tooltip("Logged out of sync.", parent=mw)
