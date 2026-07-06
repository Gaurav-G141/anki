# Speedrun sync — self-hosted server, desktop setup, and the no-loss guarantee

_Last updated: 2026-07-05._

This documents two-way sync between the desktop and the iOS Speedrun app. Both
apps drive the **same Rust engine** (`rslib`), which already implements Anki's
USN-based, transactional sync — so "no lost or double-counted reviews" and
offline-then-reconnect come from the engine, not from app-specific code.

Status:

- ✅ **Engine sync + guarantee test** — done (this file's §4; test in
  `rslib/src/sync/collection/tests.rs`).
- ✅ **Self-hosted server + desktop path** — done/documented here (§2–§3).
- ✅ **iOS app sync** — done. Manual sync button + login sheet
  (`CollectionStore.login/sync`, `DeckListView`), full-sync bootstrap
  (`fullSyncLocked`), and **offline auto-sync on reconnect/foreground**
  (`NWPathMonitor` + `needsSync` + `autoSyncIfNeeded`; §6). Call sequence in §5.
  Runs on both the Simulator build and the **new iOS device build** (§7).
- ⚠️ **Same-card conflict harness** — still open. The USN incremental merge
  handles conflicts at the engine level (last-writer-wins per object, no
  corruption), and add/add divergence is covered by §4, but there is **no
  committed automated two-device same-card conflict test** — that case has only
  been reasoned about / reproduced manually.

## 1. How it works (why reviews are never lost or doubled)

Every object (card/note/deck/**revlog**/config) carries a USN. Local edits are
written pending (`usn = -1`). A **normal (incremental) sync** exchanges only
objects newer than each side's last-sync watermark, inside a DB transaction that
rolls back on any error; on success each side advances its USN to `server_usn+1`.
So the same change is never re-sent (no double-count) and a failed/interrupted
sync leaves both sides unchanged (no partial merge). A **full sync** is
one-directional (upload clobbers remote / download clobbers local) and only fires
when the schema diverges or one side is empty — used once at bootstrap, then never
again in normal use. Offline review just means the sync RPC fails; the reviews are
already committed locally and merge in on the next successful sync.

## 2. Run the self-hosted sync server (on the Mac)

The server ships in-tree (`rslib/sync/http_server/`, binary crate
`anki-sync-server`). Pick any user/pass and a data dir:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
SYNC_HOST=0.0.0.0 SYNC_PORT=8080 SYNC_BASE=~/speedrun-sync SYNC_USER1=demo:demo \
  cargo run -p anki-sync-server
# (equivalently: `anki --syncserver` with the same SYNC_* env vars)
```

- Config is read from `SYNC_*` env vars (`SYNC_HOST` default `0.0.0.0`,
  `SYNC_PORT` default `8080`, `SYNC_BASE` default `~/.syncserver`, `SYNC_USER1`
  **required**, form `user:pass`). The server derives its own key
  `hkey = sha1("demo:demo")` — deliberately different from AnkiWeb.
- Client endpoint: `http://127.0.0.1:8080`. The **iOS Simulator shares the Mac's
  loopback**, so `127.0.0.1` works from the Simulator; a physical device needs the
  Mac's LAN IP (server already binds `0.0.0.0`).

**AnkiWeb instead:** skip the server; use a real AnkiWeb account and leave the
endpoint blank/default. The app flow is identical (login → sync).

## 3. Point the desktop at it + bootstrap

1. Desktop Anki → **Preferences → Syncing → Self-hosted sync server** →
   `http://127.0.0.1:8080` (this sets `pm.set_custom_sync_url`).
2. **Sync** (toolbar) → log in `demo` / `demo`.
3. The first Sync is the **bootstrap upload**: it pushes the desktop's collection
   (the 9 PGRE subject decks + Speed Recall) to the server, so both devices end up
   on the _same_ collection. From then on the phone's first sync is a one-time
   `FULL_DOWNLOAD` to adopt it, and everything after is incremental two-way sync.

> Sequence the demo so the phone **adopts** the shared collection (its first
> download) before you rely on it for real review — any phone reviews done on the
> throwaway starter deck _before_ adoption are discarded by that first download.

## 4. The guarantee, tested (`no lost or double-counted reviews`)

`rslib/src/sync/collection/tests.rs::revlogs_are_never_lost_or_double_counted`
runs two real collections against the in-tree server and asserts:

- reviews done on col1 ("phone") appear on col2 ("desktop") after sync, and the
  reverse;
- reviews done on **both** sides while unsynced (the offline case) merge so the
  **union is present on both** and **each revlog id appears exactly once**.

Run it:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
cargo test -p anki --lib sync::collection::tests
```

## 5. iOS call sequence (as implemented in `CollectionStore`)

All calls go through the existing generic FFI (`AnkiEngine.command(service,
method, …)`) off the main thread; **Sync = service 1**. `sync.pb.swift` is already
generated.

- **Login:** SyncLogin (1/3) with `{username, password, endpoint}` → `SyncAuth`;
  store `hkey` (Keychain) + endpoint (UserDefaults).
- **Two-way sync:** SyncCollection (1/5, `sync_media:false`) → response.
  `NO_CHANGES`/`NORMAL_SYNC` ⇒ done (merged). Any `FULL_*` ⇒ FullUploadOrDownload
  (1/6) **directly** — do **not** CloseCollection first / OpenCollection after:
  the backend's `full_sync_inner` requires the collection open and reopens it
  itself. On a full **download**, refresh the review session (the on-disk
  collection was replaced).
- **Offline → reconnect:** reviews already commit locally; keep a "dirty" flag and
  call sync on foreground and on `NWPathMonitor` connectivity-restored. No custom
  review queue is needed — the engine's USN merge handles it.
- **Media:** the decks are LaTeX (no media files) → pass `sync_media:false` and
  skip SyncMedia.

## 6. Offline review → reconnect → auto-sync (iOS)

Reviewing offline needs no special code: the phone reviews against the _local_
collection, and each `answer_card` commits to local SQLite. Those answers are
pending (`usn = -1`) until the next sync. The auto-sync wiring:

- `ReviewSession.grade()` calls `store.markReviewed()` after each answer →
  `CollectionStore.needsSync = true` (an orange dot on the sync button).
- `CollectionStore` runs an `NWPathMonitor`; on the **offline→online** edge, and
  on **app foreground** (`RootView` `scenePhase == .active`), it calls
  `autoSyncIfNeeded()` → `sync(auto: true)` when logged in + `needsSync` + online.
- A successful sync clears `needsSync`. An auto-sync that fails (still offline)
  stays quiet, keeps `needsSync`, and retries on the next reconnect/foreground —
  the manual Sync button still surfaces errors.
- Because the merge is Anki's USN incremental sync, offline reviews (even on both
  devices at once) merge with none lost or double-counted (proven in §4).

**iOS caveat:** auto-sync fires while the app is in the **foreground**; if the
phone regains signal while the app is suspended, it syncs on the next foreground
(or a Sync tap), not silently in the background. Meets "review offline → get back
online → sync."

### Interactive E2E (offline)

1. Start the server (§2); desktop → login + Sync (bootstrap upload).
2. iOS: open the app → tap the sync button → log in (`demo`/`demo`,
   `http://127.0.0.1:8080`) → first sync does a **full download** (adopts the
   shared collection).
3. Put the machine offline (disable Wi-Fi, or Simulator → Features → Network
   Link Conditioner / pull the Mac's network). Review several cards on the phone →
   the sync button shows the **orange "unsynced" dot**.
4. Restore the connection (and/or background→foreground the app). The phone
   **auto-syncs**; the dot clears.
5. Sync the desktop → it shows exactly those reviews, none lost or duplicated;
   review on the desktop, Sync, then foreground the phone → the phone auto-syncs
   them back.

## 7. Syncing from a real iPhone (new device build)

There is now an **iOS device build** in addition to the Simulator build, so the
sync flow can be exercised on real hardware:

- **Artifact:** `installers/SpeedrunApp-iOS-device-unsigned.ipa` (~22 MB). Real
  `arm64` `platform IOS` Mach-O (min iOS 15), bundle id `net.ankiweb.speedrun`,
  PGRE deck bundled. Simulator build stays at
  `installers/SpeedrunApp-iOS-Simulator.zip`.
- **UNSIGNED:** sideload via Sideloadly / AltStore (re-sign with your Apple ID),
  or re-export signed once an Apple ID/team is added. **Not TestFlight** (no paid
  Apple account on the build machine).
- **Endpoint on device:** unlike the Simulator (which shares the Mac's loopback,
  so `127.0.0.1` works), a physical iPhone must point at the **Mac's LAN IP**
  (the self-hosted server already binds `0.0.0.0`), or use a real AnkiWeb
  account. Everything else in §5–§6 is identical — same USN merge, same
  foreground-only auto-sync.

## Notes / gotchas

- Clock skew > 300 s aborts a sync (the Simulator shares the Mac clock; a physical
  device needs automatic time).
- The desktop `just check` gate is unaffected by this work (Rust test only; the
  iOS changes are Swift, outside the gate).
