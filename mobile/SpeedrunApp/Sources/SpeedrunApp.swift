// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Speedrun PGRE — iOS review app running on the shared Anki Rust engine via the
// C FFI (mobile/AnkiCore.xcframework). Home screen is a deck list; tap a deck to
// review it. No sync, no scoring (later specs).

import SwiftUI

@main
struct SpeedrunApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

/// Owns the app's single shared engine (`CollectionStore`) and hosts navigation.
struct RootView: View {
    @StateObject private var store = CollectionStore()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        NavigationView {
            DeckListView(store: store)
        }
        .navigationViewStyle(.stack)
        .onAppear { store.open() }
        .onChange(of: scenePhase) { newPhase in
            // Checkpoint graded progress into collection.anki2 when the app
            // leaves the foreground, so the on-disk database is always complete.
            if newPhase == .background {
                store.flush()
            } else if newPhase == .active {
                // Returning to the app is a natural "connection may be back" moment:
                // push any offline reviews. No-op unless logged in + something to sync.
                store.autoSyncIfNeeded()
            }
        }
    }
}
