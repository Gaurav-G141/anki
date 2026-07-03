// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// The app's home screen: a deck list (like AnkiMobile) over the shared engine.
// Tap a deck to study it (deck-scoped review); use "+" to create a new empty
// deck or import a bundled PGRE subject deck. Everything routes through the one
// `CollectionStore` engine — no scheduler logic lives in Swift.

import SwiftUI

struct DeckListView: View {
    @ObservedObject var store: CollectionStore

    @State private var showNewDeckAlert = false
    @State private var newDeckName = ""
    @State private var showImportSheet = false
    @State private var showLogin = false

    var body: some View {
        Group {
            switch store.phase {
            case .loading:
                StatusState(kind: .loading("Opening collection…"))
            case let .error(message):
                errorView(message)
            case .ready:
                deckList
            }
        }
        .navigationTitle("Decks")
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                if store.isSyncing {
                    ProgressView()
                } else if store.isLoggedIn {
                    // Logged in: tap the account button for a menu (Sync now /
                    // Log out) instead of a hidden long-press.
                    Menu {
                        if !store.syncUsername.isEmpty {
                            Section("Signed in as \(store.syncUsername)") {}
                        }
                        Button {
                            store.sync()
                        } label: {
                            Label("Sync Now", systemImage: "arrow.triangle.2.circlepath")
                        }
                        .accessibilityIdentifier("syncNow")
                        Divider()
                        Button(role: .destructive) {
                            store.logout()
                        } label: {
                            Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
                        }
                        .accessibilityIdentifier("logout")
                    } label: {
                        accountIcon
                    }
                    .accessibilityIdentifier("syncButton")
                    .disabled(store.phase != .ready)
                } else {
                    // Logged out: tap goes straight to the login sheet.
                    Button {
                        showLogin = true
                    } label: {
                        Image(systemName: "person.crop.circle.badge.plus")
                            .foregroundColor(Palette.accent)
                    }
                    .accessibilityIdentifier("syncButton")
                    .disabled(store.phase != .ready)
                }
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink {
                    ScoresView(store: store)
                } label: {
                    Image(systemName: "chart.bar")
                        .foregroundColor(Palette.accent)
                }
                .accessibilityIdentifier("scores")
                .disabled(store.phase != .ready)
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink {
                    MCQView()
                } label: {
                    Image(systemName: "target")
                        .foregroundColor(Palette.accent)
                }
                .accessibilityIdentifier("openMCQ")
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button {
                        newDeckName = ""
                        showNewDeckAlert = true
                    } label: {
                        Label("New Deck", systemImage: "plus.rectangle.on.folder")
                    }
                    Button {
                        showImportSheet = true
                    } label: {
                        Label("Import Deck", systemImage: "square.and.arrow.down")
                    }
                } label: {
                    Image(systemName: "plus")
                        .foregroundColor(Palette.accent)
                }
                .accessibilityIdentifier("addDeck")
                .disabled(store.isBusy || store.phase != .ready)
            }
        }
        .alert("New Deck", isPresented: $showNewDeckAlert) {
            TextField("Deck name", text: $newDeckName)
                .accessibilityIdentifier("newDeckName")
            Button("Cancel", role: .cancel) {}
            Button("Create") { store.createDeck(named: newDeckName) }
                .accessibilityIdentifier("createDeckConfirm")
        } message: {
            Text("Create a new empty deck. Add cards on the desktop and sync.")
        }
        .sheet(isPresented: $showImportSheet) {
            ImportDeckSheet(store: store, isPresented: $showImportSheet)
        }
        .sheet(isPresented: $showLogin) {
            LoginSheet(store: store, isPresented: $showLogin)
        }
        .alert("Sync error", isPresented: Binding(
            get: { store.syncError != nil },
            set: { if !$0 { store.syncError = nil } }
        )) {
            Button("OK", role: .cancel) { store.syncError = nil }
        } message: {
            Text(store.syncError ?? "")
        }
    }

    /// The logged-in toolbar icon: a sync glyph with an amber dot when there are
    /// local reviews not yet pushed (e.g. done offline).
    private var accountIcon: some View {
        Image(systemName: "arrow.triangle.2.circlepath")
            .foregroundColor(Palette.accent)
            .overlay(alignment: .topTrailing) {
                if store.needsSync {
                    Circle().fill(Palette.warn)
                        .frame(width: 8, height: 8)
                        .offset(x: 5, y: -5)
                        .accessibilityIdentifier("unsyncedDot")
                }
            }
    }

    private var deckList: some View {
        List {
            Section {
                NavigationLink {
                    MCQView()
                } label: {
                    heroMCQRow
                }
                .accessibilityIdentifier("openMCQrow")
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
            } header: {
                Eyebrow("Performance")
            }
            Section {
                if store.decks.isEmpty {
                    StatusState(kind: .empty("✧", "No decks yet. Tap + to create or import one."))
                        .frame(minHeight: 160)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                } else {
                    ForEach(store.decks) { node in
                        NavigationLink {
                            ReviewView(store: store, deckId: node.id, deckName: node.name)
                        } label: {
                            deckRow(node)
                        }
                        .accessibilityIdentifier("deck_\(node.name)")
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                }
            } header: {
                Eyebrow("Decks")
            }
        }
        .listStyle(.plain)
        .refreshable { store.reloadDeckTree() }
        .overlay {
            if store.isBusy {
                ProgressView()
                    .tint(Palette.accent)
                    .padding(22)
                    .background(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(Palette.panel2))
            }
        }
    }

    /// The prominent cyan hero row that launches the MCQ practice flow.
    private var heroMCQRow: some View {
        HStack(spacing: 14) {
            Image(systemName: "atom")
                .font(.title2)
                .foregroundColor(Palette.accent)
            VStack(alignment: .leading, spacing: 3) {
                Text("Practice MCQs")
                    .font(.pgTitle)
                    .foregroundColor(Palette.text)
                Text("Real exam questions")
                    .font(.pgMono(11))
                    .tracking(1.2)
                    .foregroundColor(Palette.textDim)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.footnote.weight(.semibold))
                .foregroundColor(Palette.accent.opacity(0.8))
        }
        .glassCard(glow: Palette.accent)
    }

    /// A cosmetic mastery fraction for the ring: how much of a deck's pending
    /// workload is mature review material vs new/learning. Purely decorative —
    /// there is no real "mastery %" behind it, so the ring carries no label.
    private func masteryPct(_ node: DeckNode) -> Double {
        let total = node.newCount + node.learnCount + node.reviewCount
        guard total > 0 else { return 0 }
        return Double(node.reviewCount) / Double(total)
    }

    private func deckRow(_ node: DeckNode) -> some View {
        HStack(spacing: 12) {
            MasteryRing(pct: masteryPct(node))
            Text(node.name)
                .font(.pgBody)
                .foregroundColor(Palette.text)
                .padding(.leading, CGFloat(node.level) * 16)
            Spacer()
            HStack(spacing: 10) {
                CountChip(count: node.newCount, kind: .new)
                CountChip(count: node.learnCount, kind: .learn)
                CountChip(count: node.reviewCount, kind: .review)
            }
        }
        .glassCard(padding: 12)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.largeTitle)
                .foregroundColor(Palette.warn)
            Text("Couldn't open the collection")
                .font(.pgTitle)
                .foregroundColor(Palette.text)
            ScrollView {
                Text(message)
                    .font(.pgMono(12))
                    .foregroundColor(Palette.textDim)
                    .multilineTextAlignment(.leading)
                    .padding()
            }
            .glassCard(padding: 4)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityIdentifier("error")
    }
}

/// Lists the bundled PGRE subject `.apkg`s. Already-imported ones are disabled.
private struct ImportDeckSheet: View {
    @ObservedObject var store: CollectionStore
    @Binding var isPresented: Bool

    var body: some View {
        NavigationView {
            List(BundledDeck.subjects) { deck in
                Button {
                    store.importBundled(deck)
                    isPresented = false
                } label: {
                    HStack {
                        Text(deck.title)
                        Spacer()
                        if store.importedPackages.contains(deck.id) {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(Palette.ok)
                        } else {
                            Image(systemName: "square.and.arrow.down")
                                .foregroundColor(Palette.accent)
                        }
                    }
                }
                .disabled(store.importedPackages.contains(deck.id))
                .accessibilityIdentifier("import_\(deck.id)")
            }
            .navigationTitle("Import Deck")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") { isPresented = false }
                }
            }
        }
    }
}

/// AnkiWeb / self-hosted login. Leave the endpoint blank for AnkiWeb, or point it
/// at a self-hosted `anki-sync-server` (e.g. http://127.0.0.1:8080).
private struct LoginSheet: View {
    @ObservedObject var store: CollectionStore
    @Binding var isPresented: Bool

    /// Which sync server to use. Explicit so AnkiWeb credentials are never sent to
    /// a self-hosted server (or vice-versa) by accident.
    enum Server: String, CaseIterable, Identifiable {
        case ankiWeb = "AnkiWeb"
        case selfHosted = "Self-hosted"
        var id: String { rawValue }
    }

    @State private var server: Server = .ankiWeb
    @State private var username = ""
    @State private var password = ""
    @State private var endpoint = "http://127.0.0.1:8080"
    @State private var busy = false

    var body: some View {
        NavigationView {
            Form {
                Section {
                    Picker("Server", selection: $server) {
                        ForEach(Server.allCases) { Text($0.rawValue).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("syncServerPicker")
                }
                Section {
                    TextField(server == .ankiWeb ? "Email" : "Username", text: $username)
                        .textContentType(.username)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .keyboardType(server == .ankiWeb ? .emailAddress : .default)
                        .accessibilityIdentifier("syncUsername")
                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .accessibilityIdentifier("syncPassword")
                }
                if server == .ankiWeb {
                    Section {} footer: {
                        Text("Sign in with your AnkiWeb email and password — the same ones that work on ankiweb.net.")
                    }
                } else {
                    Section {
                        TextField("Server URL", text: $endpoint)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .keyboardType(.URL)
                            .accessibilityIdentifier("syncEndpoint")
                    } footer: {
                        Text("Base URL of your anki-sync-server, e.g. http://127.0.0.1:8080 (no /sync path). On the Simulator use 127.0.0.1; on a real device use your Mac's LAN IP (e.g. http://192.168.x.x:8080), since 127.0.0.1 is the phone itself.")
                    }
                }
                Section {
                    Button {
                        busy = true
                        // AnkiWeb ⇒ blank endpoint; self-hosted ⇒ the entered URL.
                        let ep = server == .ankiWeb ? "" : endpoint
                        store.login(username: username, password: password, endpoint: ep) { ok in
                            busy = false
                            if ok { isPresented = false }
                        }
                    } label: {
                        HStack {
                            Text("Log in")
                            if busy { Spacer(); ProgressView() }
                        }
                    }
                    .disabled(busy || username.isEmpty || password.isEmpty)
                    .accessibilityIdentifier("syncLoginConfirm")
                }
            }
            .navigationTitle("Sync Login")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { isPresented = false }
                }
            }
        }
    }
}
