// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Speedrun PGRE — minimal iOS review app running on the shared Anki Rust engine
// via the C FFI (mobile/AnkiCore.xcframework). No sync, no scoring (later specs).

import SwiftUI

@main
struct SpeedrunApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
