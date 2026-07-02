// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Owns the ONE shared Anki engine for the whole app. The desktop and this app
// run the *same* Rust core (mobile/AnkiCore.xcframework == rslib); this type is
// just the single Swift-side owner of one `AnkiEngine` (one backend + one open
// collection) plus the serial queue every FFI call runs on. Deck listing,
// creation, import, and the review session (see `ReviewSession`) all go through
// this one engine — nothing reimplements the scheduler in Swift.

import Foundation
import Network
import SwiftProtobuf
import SwiftUI

/// One row in the deck list (a flattened `DeckTreeNode`).
struct DeckNode: Identifiable, Equatable {
    let id: Int64  // deck id; pass to SetCurrentDeck
    let name: String  // leaf display name (Anki's DeckTreeNode.name)
    let level: Int  // nesting depth, for indentation
    let newCount: Int
    let learnCount: Int
    let reviewCount: Int
}

/// A bundled `.apkg` the user can import from the "+" menu.
struct BundledDeck: Identifiable, Hashable {
    let id: String  // resource filename (without extension)
    let title: String  // human label
    static let subjects: [BundledDeck] = [
        .init(id: "01_Classical_Mechanics", title: "Classical Mechanics"),
        .init(id: "02_Electromagnetism", title: "Electromagnetism"),
        .init(id: "03_Quantum_Mechanics", title: "Quantum Mechanics"),
        .init(id: "04_Atomic_Physics", title: "Atomic Physics"),
        .init(id: "05_Thermodynamics_Statistical_Mechanics", title: "Thermodynamics & Statistical Mechanics"),
        .init(id: "06_Optics_Waves", title: "Optics & Waves"),
        .init(id: "07_Specialized_Topics", title: "Specialized Topics"),
        .init(id: "08_Special_Relativity", title: "Special Relativity"),
        .init(id: "09_Laboratory_Methods", title: "Laboratory Methods"),
    ]
}

@MainActor
final class CollectionStore: ObservableObject {
    enum Phase: Equatable {
        case loading
        case ready
        case error(String)
    }

    @Published private(set) var phase: Phase = .loading
    @Published private(set) var decks: [DeckNode] = []
    /// True while a create/import is running (drives a spinner + disables "+").
    @Published private(set) var isBusy = false
    /// Filenames of bundled packages already imported (persisted, for idempotency).
    @Published private(set) var importedPackages: Set<String> = []

    // Sync (AnkiWeb or self-hosted server). The engine (rslib) does the USN merge;
    // these just drive the login sheet + Sync button.
    @Published private(set) var isLoggedIn = false
    /// The logged-in account (AnkiWeb email or self-hosted username), for display
    /// in the account menu. Empty when logged out.
    @Published private(set) var syncUsername = ""
    @Published private(set) var isSyncing = false
    /// Last sync error (nil when clear); bound to an alert.
    @Published var syncError: String?
    /// Short human status after a successful sync (e.g. "Downloaded", "Up to date").
    @Published private(set) var lastSyncMessage: String?
    /// True when local reviews haven't been pushed to the server yet. Drives the
    /// "unsynced" indicator and auto-sync when the connection returns.
    @Published private(set) var needsSync = false

    /// The single serial queue every FFI call runs on. `ReviewSession` reuses it
    /// so review and deck ops never touch the (non-thread-safe) engine at once.
    let queue = DispatchQueue(label: "net.ankiweb.speedrun.engine")
    /// The single engine handle. Non-nil once `open()` succeeds (before any deck
    /// is selected). `ReviewSession` reads this to drive its review loop.
    private(set) var engine: AnkiEngine?

    private var collectionPath = ""
    private var mediaFolder = ""
    private var mediaDB = ""

    // Connectivity watch, so offline reviews auto-sync when the connection returns.
    private let pathMonitor = NWPathMonitor()
    private var isOnline = true
    private var monitorStarted = false

    private let importedKey = "speedrun.importedPackages"

    // In-memory sync credential; hkey + endpoint persist in UserDefaults so login
    // survives relaunch. (A self-hosted demo hkey is not sensitive; use Keychain
    // if pointing at a real AnkiWeb account long-term.)
    private var syncAuth: Anki_Sync_SyncAuth?
    private let hkeyKey = "speedrun.sync.hkey"
    private let endpointKey = "speedrun.sync.endpoint"
    private let usernameKey = "speedrun.sync.username"

    // MARK: - Lifecycle

    /// Opens the shared engine + collection once, then loads the deck list.
    func open() {
        phase = .loading
        startNetworkMonitoring()
        importedPackages = Set(UserDefaults.standard.stringArray(forKey: importedKey) ?? [])
        queue.async { [weak self] in
            guard let self else { return }
            do {
                self.collectionPath = try Self.prepareCollectionPath()
                self.mediaFolder = try Self.prepareMediaFolder()
                _ = try Self.prepareMathjax()
                self.mediaDB = Self.documentsURL().appendingPathComponent("collection.media.db").path

                var initProto = Anki_Backend_BackendInit()
                initProto.preferredLangs = []
                let engine = try AnkiEngine.open(init: initProto)
                try self.openCollectionLocked(engine: engine)
                self.engine = engine
                self.loadPersistedAuthLocked()

                let nodes = try self.deckTreeLocked(engine: engine)
                DispatchQueue.main.async {
                    self.decks = nodes
                    self.phase = .ready
                    // Cold-launch pull: the scenePhase→.active hook can fire before
                    // the persisted credential finished loading, so kick a sync here
                    // too (no-op if logged out) to pull any desktop changes on open.
                    self.autoSyncIfNeeded()
                }
            } catch {
                DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
            }
        }
    }

    /// Checkpoints graded progress into `collection.anki2` (close → reopen) when
    /// the app backgrounds, so the on-disk database is always complete. Same
    /// logic the review screen used before; centralized on the single engine.
    func flush() {
        queue.async { [weak self] in
            guard let self, let engine = self.engine else { return }
            do {
                var closeReq = Anki_Collection_CloseCollectionRequest()
                closeReq.downgradeToSchema11 = false
                _ = try engine.command(
                    service: AnkiService.collection,
                    method: AnkiMethod.closeCollection,
                    request: closeReq,
                    response: Anki_Generic_Empty.self
                )
                try self.openCollectionLocked(engine: engine)
            } catch {
                DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
            }
        }
    }

    /// Reloads the deck tree (call after returning from a review, or after a
    /// create/import) so due counts stay fresh.
    func reloadDeckTree() {
        queue.async { [weak self] in
            guard let self, let engine = self.engine else { return }
            do {
                let nodes = try self.deckTreeLocked(engine: engine)
                DispatchQueue.main.async { self.decks = nodes }
            } catch {
                DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
            }
        }
    }

    // MARK: - Deck operations (all on the shared engine)

    /// Creates a new empty deck (NewDeck → set name → AddDeck), then reloads.
    /// Mirrors desktop `Collection.decks.add_normal_deck_with_name`.
    func createDeck(named name: String) {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        runMutating { engine in
            var deck = try engine.command(
                service: AnkiService.decks, method: AnkiMethod.newDeck,
                request: Anki_Generic_Empty(), response: Anki_Decks_Deck.self
            )
            deck.name = trimmed
            _ = try engine.command(
                service: AnkiService.decks, method: AnkiMethod.addDeck,
                request: deck, response: Anki_Collection_OpChangesWithId.self
            )
        }
    }

    /// Imports a bundled `.apkg` into the open collection (ImportAnkiPackage),
    /// then reloads. Anki's GUID-based note dedupe means a re-import updates
    /// rather than duplicates. Mirrors desktop `Collection.import_anki_package`.
    func importBundled(_ deck: BundledDeck) {
        guard let url = Bundle.main.url(forResource: deck.id, withExtension: "apkg") else {
            phase = .error("bundled deck \(deck.id).apkg not found in app bundle")
            return
        }
        runMutating(then: { [weak self] in
            self?.markImported(deck.id)
        }, work: { engine in
            var req = Anki_ImportExport_ImportAnkiPackageRequest()
            req.packagePath = url.path
            req.options = Anki_ImportExport_ImportAnkiPackageOptions()  // defaults
            _ = try engine.command(
                service: AnkiService.importExport, method: AnkiMethod.importAnkiPackage,
                request: req, response: Anki_ImportExport_ImportResponse.self
            )
        })
    }

    // MARK: - Sync (shared engine; USN merge lives in rslib)

    /// Logs in to AnkiWeb (blank endpoint) or a self-hosted server (custom
    /// endpoint) via SyncLogin, storing the returned `hkey`. `completion(true)`
    /// on success so the login sheet can dismiss.
    func login(username: String, password: String, endpoint: String,
               completion: @escaping (Bool) -> Void) {
        queue.async { [weak self] in
            guard let self, let engine = self.engine else {
                DispatchQueue.main.async { completion(false) }
                return
            }
            do {
                var req = Anki_Sync_SyncLoginRequest()
                req.username = username
                req.password = password
                let ep = Self.normalizedEndpoint(endpoint)
                if !ep.isEmpty { req.endpoint = ep }

                let auth = try engine.command(
                    service: AnkiService.sync, method: AnkiMethod.syncLogin,
                    request: req, response: Anki_Sync_SyncAuth.self
                )
                self.storeAuthLocked(auth, fallbackEndpoint: ep)
                UserDefaults.standard.set(username, forKey: self.usernameKey)
                DispatchQueue.main.async {
                    self.isLoggedIn = true
                    self.syncUsername = username
                    self.syncError = nil
                    completion(true)
                    // Immediately sync so logging in visibly pulls the shared
                    // collection (first login = full download), like the desktop.
                    self.sync()
                }
            } catch {
                DispatchQueue.main.async {
                    self.syncError = String(describing: error)
                    completion(false)
                }
            }
        }
    }

    /// Two-way sync. A normal sync merges silently; any FULL_* escalates to
    /// FullUploadOrDownload (the phone adopts the server's collection on first
    /// sync via a full download). Reloads the deck tree afterwards.
    func sync(auto: Bool = false) {
        guard let auth0 = syncAuth else { return }
        isSyncing = true
        if !auto { syncError = nil }
        queue.async { [weak self] in
            guard let self, let engine = self.engine else { return }
            do {
                var auth = auth0
                var req = Anki_Sync_SyncCollectionRequest()
                req.auth = auth
                req.syncMedia = false  // LaTeX decks have no media

                let resp = try engine.command(
                    service: AnkiService.sync, method: AnkiMethod.syncCollection,
                    request: req, response: Anki_Sync_SyncCollectionResponse.self
                )
                // AnkiWeb may hand back a load-balanced endpoint; use it from here.
                if resp.hasNewEndpoint, !resp.newEndpoint.isEmpty {
                    auth.endpoint = resp.newEndpoint
                    self.storeAuthLocked(auth, fallbackEndpoint: "")
                }

                var message: String
                switch resp.required {
                case .fullDownload, .fullSync:
                    try self.fullSyncLocked(engine: engine, auth: auth, upload: false)
                    message = "Downloaded full collection"
                case .fullUpload:
                    try self.fullSyncLocked(engine: engine, auth: auth, upload: true)
                    message = "Uploaded full collection"
                case .normalSync:
                    message = "Synced"
                default:
                    message = "Up to date"
                }

                let nodes = try self.deckTreeLocked(engine: engine)
                DispatchQueue.main.async {
                    self.decks = nodes
                    self.isSyncing = false
                    self.needsSync = false  // local reviews are now on the server
                    self.lastSyncMessage = message
                }
            } catch {
                DispatchQueue.main.async {
                    self.isSyncing = false
                    // Auto-sync failures are usually just "offline" — stay quiet and
                    // keep `needsSync` so we retry on the next reconnect/foreground.
                    // A manual sync (user tapped the button) surfaces the error.
                    if auto {
                        self.lastSyncMessage = "Offline — will sync when back online"
                    } else {
                        self.syncError = String(describing: error)
                    }
                }
            }
        }
    }

    /// Marks that local reviews haven't been pushed yet (called after each grade).
    func markReviewed() { needsSync = true }

    /// Auto-syncs whenever we're logged in and online. Triggered on app
    /// foreground and when the connection returns. Crucially this does NOT require
    /// local changes (`needsSync`): a normal sync is two-way, so it must run even
    /// with nothing to push in order to *pull* work done on other devices (e.g.
    /// reviews you did on the desktop). If nothing changed on either side the
    /// server reports "no changes" and it's a cheap no-op.
    func autoSyncIfNeeded() {
        guard isLoggedIn, !isSyncing, isOnline, syncAuth != nil else { return }
        sync(auto: true)
    }

    /// Watches connectivity; when the connection returns, auto-syncs any pending
    /// reviews. Idempotent — starts the monitor once.
    private func startNetworkMonitoring() {
        guard !monitorStarted else { return }
        monitorStarted = true
        pathMonitor.pathUpdateHandler = { [weak self] path in
            let online = path.status == .satisfied
            DispatchQueue.main.async {
                guard let self else { return }
                let cameOnline = online && !self.isOnline
                self.isOnline = online
                if cameOnline { self.autoSyncIfNeeded() }
            }
        }
        pathMonitor.start(queue: DispatchQueue(label: "net.ankiweb.speedrun.netmonitor"))
    }

    /// Logs out: clears the stored credential AND resets the on-disk collection
    /// back to the bundled starter decks, so the account's synced decks no longer
    /// appear on this device. This is safe — that data lives on the server, and
    /// logging back in re-downloads it (a fresh local collection differs from the
    /// server, so the first sync is a full download again).
    func logout() {
        // Credential + UI state (we're on the main thread from the menu action).
        syncAuth = nil
        isLoggedIn = false
        syncUsername = ""
        lastSyncMessage = nil
        needsSync = false
        importedPackages = []
        UserDefaults.standard.removeObject(forKey: hkeyKey)
        UserDefaults.standard.removeObject(forKey: endpointKey)
        UserDefaults.standard.removeObject(forKey: usernameKey)
        UserDefaults.standard.removeObject(forKey: importedKey)

        // Replace the local collection with the bundled starter, off the main
        // thread on the shared engine queue, then refresh the deck list.
        queue.async { [weak self] in
            guard let self, let engine = self.engine else { return }
            do {
                try self.resetCollectionToBundledLocked(engine: engine)
                let nodes = try self.deckTreeLocked(engine: engine)
                DispatchQueue.main.async { self.decks = nodes }
            } catch {
                DispatchQueue.main.async { self.phase = .error(String(describing: error)) }
            }
        }
    }

    /// Closes the collection, deletes the local `collection.anki2` (+ WAL/SHM),
    /// re-seeds it from the bundled starter deck, and reopens. Runs on `queue`.
    private func resetCollectionToBundledLocked(engine: AnkiEngine) throws {
        // Release the SQLite handle before replacing the file on disk.
        var closeReq = Anki_Collection_CloseCollectionRequest()
        closeReq.downgradeToSchema11 = false
        _ = try engine.command(
            service: AnkiService.collection, method: AnkiMethod.closeCollection,
            request: closeReq, response: Anki_Generic_Empty.self
        )

        let fm = FileManager.default
        let dest = Self.documentsURL().appendingPathComponent("collection.anki2")
        for suffix in ["", "-wal", "-shm"] {
            let path = dest.path + suffix
            if fm.fileExists(atPath: path) { try fm.removeItem(atPath: path) }
        }
        guard let bundled = Bundle.main.url(forResource: "pgre_exam", withExtension: "anki2") else {
            throw AnkiEngineError.openBackendFailed("bundled deck pgre_exam.anki2 not found in app bundle")
        }
        try fm.copyItem(at: bundled, to: dest)
        self.collectionPath = dest.path
        try self.openCollectionLocked(engine: engine)
    }

    private func fullSyncLocked(engine: AnkiEngine, auth: Anki_Sync_SyncAuth, upload: Bool) throws {
        var req = Anki_Sync_FullUploadOrDownloadRequest()
        req.auth = auth
        req.upload = upload
        // Per Anki: the collection stays open across a full sync; the backend
        // reopens it itself. Do NOT close/open around this call.
        _ = try engine.command(
            service: AnkiService.sync, method: AnkiMethod.fullUploadOrDownload,
            request: req, response: Anki_Generic_Empty.self
        )
    }

    /// Persists + caches the auth. Must run on `queue`.
    private func storeAuthLocked(_ auth: Anki_Sync_SyncAuth, fallbackEndpoint: String) {
        var a = auth
        if a.endpoint.isEmpty, !fallbackEndpoint.isEmpty { a.endpoint = fallbackEndpoint }
        self.syncAuth = a
        UserDefaults.standard.set(a.hkey, forKey: hkeyKey)
        UserDefaults.standard.set(a.endpoint, forKey: endpointKey)
    }

    /// Restores a saved credential on launch. Must run on `queue`.
    private func loadPersistedAuthLocked() {
        guard let hkey = UserDefaults.standard.string(forKey: hkeyKey), !hkey.isEmpty else { return }
        var a = Anki_Sync_SyncAuth()
        a.hkey = hkey
        let ep = UserDefaults.standard.string(forKey: endpointKey) ?? ""
        if !ep.isEmpty { a.endpoint = ep }
        self.syncAuth = a
        let user = UserDefaults.standard.string(forKey: usernameKey) ?? ""
        DispatchQueue.main.async {
            self.isLoggedIn = true
            self.syncUsername = user
        }
    }

    // MARK: - Private helpers

    /// Runs a mutating engine op off the main thread, toggling `isBusy`, then
    /// reloads the deck tree (and runs an optional main-thread completion).
    private func runMutating(then completion: (() -> Void)? = nil,
                             work: @escaping (AnkiEngine) throws -> Void) {
        isBusy = true
        queue.async { [weak self] in
            guard let self, let engine = self.engine else { return }
            do {
                try work(engine)
                let nodes = try self.deckTreeLocked(engine: engine)
                DispatchQueue.main.async {
                    self.decks = nodes
                    self.isBusy = false
                    completion?()
                }
            } catch {
                DispatchQueue.main.async {
                    self.isBusy = false
                    self.phase = .error(String(describing: error))
                }
            }
        }
    }

    private func markImported(_ id: String) {
        importedPackages.insert(id)
        UserDefaults.standard.set(Array(importedPackages), forKey: importedKey)
    }

    /// Fetches + flattens the deck tree. Must run on `queue`.
    private func deckTreeLocked(engine: AnkiEngine) throws -> [DeckNode] {
        var req = Anki_Decks_DeckTreeRequest()
        req.now = Int64(Date().timeIntervalSince1970)
        let root = try engine.command(
            service: AnkiService.decks, method: AnkiMethod.deckTree,
            request: req, response: Anki_Decks_DeckTreeNode.self
        )
        var out: [DeckNode] = []
        Self.flatten(root.children, into: &out)
        return out
    }

    /// Depth-first flatten of the tree's children into display rows. Hides the
    /// empty "Default" deck (id 1) the way Anki's deck list does.
    private static func flatten(_ nodes: [Anki_Decks_DeckTreeNode], into out: inout [DeckNode]) {
        for node in nodes {
            let isEmptyDefault = node.deckID == 1
                && node.newCount == 0 && node.learnCount == 0 && node.reviewCount == 0
                && node.children.isEmpty
            if !isEmptyDefault {
                out.append(DeckNode(
                    id: node.deckID, name: node.name, level: Int(node.level),
                    newCount: Int(node.newCount), learnCount: Int(node.learnCount),
                    reviewCount: Int(node.reviewCount)
                ))
            }
            Self.flatten(node.children, into: &out)
        }
    }

    /// Opens the collection on `engine` from the captured paths. Must run on
    /// `queue`. Shared by `open` (initial) and `flush` (reopen after close).
    private func openCollectionLocked(engine: AnkiEngine) throws {
        var openReq = Anki_Collection_OpenCollectionRequest()
        openReq.collectionPath = collectionPath
        openReq.mediaFolderPath = mediaFolder
        openReq.mediaDbPath = mediaDB
        _ = try engine.command(
            service: AnkiService.collection, method: AnkiMethod.openCollection,
            request: openReq, response: Anki_Generic_Empty.self
        )
    }

    // MARK: - Filesystem setup (moved from ReviewSession)

    static func documentsURL() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    /// Normalizes a user-typed sync endpoint to the bare base URL Anki expects
    /// (it appends `/sync/...` itself). Fixes the common mistakes that yield a
    /// 404 or "invalid sync server": missing scheme, trailing slash, or an
    /// accidental `/sync` path. Empty input ⇒ AnkiWeb (returned unchanged).
    static func normalizedEndpoint(_ raw: String) -> String {
        var s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.isEmpty { return "" }
        if !s.contains("://") { s = "http://" + s }
        while s.hasSuffix("/") { s.removeLast() }
        for path in ["/sync", "/msync"] where s.hasSuffix(path) {
            s.removeLast(path.count)
        }
        while s.hasSuffix("/") { s.removeLast() }
        return s
    }

    /// Copies the bundled `pgre_exam.anki2` to `Documents/collection.anki2` on
    /// first launch, returning the destination path.
    private static func prepareCollectionPath() throws -> String {
        let dest = documentsURL().appendingPathComponent("collection.anki2")
        let fm = FileManager.default
        if !fm.fileExists(atPath: dest.path) {
            guard let bundled = Bundle.main.url(forResource: "pgre_exam", withExtension: "anki2") else {
                throw AnkiEngineError.openBackendFailed("bundled deck pgre_exam.anki2 not found in app bundle")
            }
            try fm.copyItem(at: bundled, to: dest)
        }
        return dest.path
    }

    /// Copies the bundled MathJax folder to `Documents/mathjax` on first launch.
    private static func prepareMathjax() throws -> String {
        let dest = documentsURL().appendingPathComponent("mathjax")
        let fm = FileManager.default
        if !fm.fileExists(atPath: dest.path) {
            guard let bundled = Bundle.main.url(forResource: "mathjax", withExtension: nil) else {
                throw AnkiEngineError.openBackendFailed("bundled mathjax folder not found in app bundle")
            }
            try fm.copyItem(at: bundled, to: dest)
        }
        return dest.path
    }

    private static func prepareMediaFolder() throws -> String {
        let media = documentsURL().appendingPathComponent("collection.media")
        let fm = FileManager.default
        if !fm.fileExists(atPath: media.path) {
            try fm.createDirectory(at: media, withIntermediateDirectories: true)
        }
        return media.path
    }
}
