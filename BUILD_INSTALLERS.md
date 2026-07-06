# Building the installers (macOS desktop + iOS simulator + iOS device)

This fork ships two apps:

- **Desktop** — the full Anki app (the "Ankimatter" Calabi-Yau home screen, the 9
  PGRE subject decks, Speed Recall, the mastery dashboard), packaged as a **macOS
  `.dmg`**.
- **iOS** — a **Speedrun** app (`mobile/SpeedrunApp`) that talks to the _same_ Rust
  core over a C-FFI (the `AnkiCore.xcframework` is `rslib`, identical to the engine
  the desktop uses). It opens on a **deck list** (like AnkiMobile): tap a deck to
  run a deck-scoped review, or use **"+"** to create a new empty deck or import a
  bundled PGRE subject deck. Buildable for both the **iOS Simulator** and a
  **physical device** (an unsigned `.ipa` for sideloading — see §3').

The prebuilt binaries are **not** committed to the repo (they're large and land
in git-ignored folders). Follow the steps below to build them from source. All
commands were run and verified on macOS 15 / Apple Silicon, Xcode 26.

---

## 0. Prerequisites (one-time)

You need an **Apple-Silicon Mac** with:

| Tool                                            | Install                                                     | Needed for |
| ----------------------------------------------- | ----------------------------------------------------------- | ---------- |
| **Xcode** (full, not just CLT) + `xcode-select` | App Store, then `sudo xcodebuild -license accept`           | both       |
| **Homebrew**                                    | https://brew.sh                                             | `just`     |
| **just**                                        | `brew install just`                                         | desktop    |
| **Rust (rustup)**                               | https://rustup.rs                                           | both       |
| iOS Rust targets                                | `rustup target add aarch64-apple-ios aarch64-apple-ios-sim` | iOS        |
| **cbindgen**                                    | `cargo install cbindgen`                                    | iOS        |

Then clone with submodules (the installer templates are git submodules):

```bash
git clone <repo-url> Anki
cd Anki
git submodule update --init --recursive
```

Make sure Cargo is on your `PATH` (the build shells out to `cargo`):

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

> Everything else — Python, `uv`, `briefcase`, Node, protobuf — is downloaded and
> pinned automatically by the build system into `out/` the first time you build.
> **Network access is required** (Briefcase downloads a Python support package +
> PyQt6/Qt; Swift Package Manager fetches swift-protobuf).

---

## 1. macOS desktop `.dmg`

From the repo root:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
RELEASE=2 ./ninja installer
```

(That is exactly what `tools/build-installer` runs; it's documented in
`docs/development.md`. There is no `just` recipe for the installer.)

This builds the `anki`/`aqt` wheels, runs Briefcase `build` then `package`, and
**ad-hoc signs** the app. First run takes several minutes. Output:

```
out/installer/dist/anki-26.05-mac-apple.dmg
```

### Install it

1. Open the `.dmg`.
2. Drag **Anki.app** onto the **Applications** shortcut.
3. Because the app is **ad-hoc signed** (no Apple Developer ID), Gatekeeper will
   block it the first time. Either:
   - Right-click **Anki.app → Open**, then confirm; **or**
   - `xattr -dr com.apple.quarantine /Applications/Anki.app`

Launch Anki, create/open a profile, and you'll land on the red manifold home
screen. As you master subjects, each spike greens (the three core subjects —
Classical Mechanics, Electromagnetism, Quantum Mechanics — stay red longer).

> Apple-Silicon only (`universal_build = false`), min macOS 13.0.

---

## 2. iOS Simulator app

### 2a. Build the Rust core as an xcframework

The `mobile/AnkiCore.xcframework` (the Rust engine compiled for iOS) is **not**
committed — build it:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
mobile/build-xcframework.sh
```

This runs `cbindgen`, compiles `anki-ffi` (release) for `aarch64-apple-ios` and
`aarch64-apple-ios-sim`, and assembles `mobile/AnkiCore.xcframework`.

### 2b. Build the app for the simulator

The Xcode project is committed, so you can build it directly (device-agnostic —
no specific simulator needs to exist yet):

```bash
xcodebuild \
  -project mobile/SpeedrunApp/SpeedrunApp.xcodeproj \
  -scheme SpeedrunApp \
  -configuration Release \
  -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath out/ios \
  build
```

Output:

```
out/ios/Build/Products/Release-iphonesimulator/SpeedrunApp.app
```

> If you edit `mobile/SpeedrunApp/project.yml` (e.g. adding files/resources),
> regenerate the project first with `brew install xcodegen` then
> `cd mobile/SpeedrunApp && xcodegen generate`. This **Simulator** build is
> unsigned (`CODE_SIGNING_ALLOWED = NO`) and runs on the Simulator only; for a
> physical iPhone use the unsigned device `.ipa` in the section below.
>
> The Swift protobuf types under `mobile/SpeedrunApp/Generated/anki/` are
> committed. If you need to (re)generate one from a `.proto` — e.g. after a proto
> change — run (with `protoc` + `protoc-gen-swift` on PATH, both from Homebrew):
> `protoc -I proto --swift_out=mobile/SpeedrunApp/Generated proto/anki/<name>.proto`.

**What's bundled (already committed — no extra step):**

- `Resources/pgre_exam.anki2` — the starting collection (a `Speed Recall` parent
  deck + 9 subject subdecks, 166 formula cards). Copied to the app's Documents on
  first launch and opened via the shared Rust engine.
- `Resources/decks/*.apkg` — the 9 full PGRE subject decks (~8 MB), importable
  in-app via **"+" → Import Deck** (`CollectionStore.importBundled` →
  `ImportAnkiPackage` on the shared engine). Re-import is safe (GUID dedupe).
- `Resources/mathjax/` — trimmed **MathJax**; card sides render in a `WKWebView`
  that typesets the LaTeX **offline**.

(To regenerate the starting collection from a different source, import an
`.apkg`/`.colpkg` into a fresh `Collection`, `col.decks.select(<deck id>)` so it
has due cards, and copy the resulting `.anki2` over `Resources/pgre_exam.anki2`.)

---

## 3. Running the iOS app in the emulator (Simulator)

The iOS "emulator" is Apple's **Simulator**, bundled with Xcode.

```bash
# 1. Open the Simulator app
open -a Simulator

# 2. See the available simulated devices
xcrun simctl list devices available | grep iPhone

# 3. Boot one (any modern iPhone works; example uses iPhone 17).
#    Skip if the Simulator already booted a device.
xcrun simctl boot "iPhone 17"

# 4. Install the app you built onto the booted simulator
xcrun simctl install booted out/ios/Build/Products/Release-iphonesimulator/SpeedrunApp.app

# 5. Launch it
xcrun simctl launch booted net.ankiweb.speedrun
```

The app opens to the **deck list** (Speed Recall + its 9 subject subdecks, each
with due counts). Tap a deck to start a **deck-scoped** review: a question shows a
prompt like "Formula for the hydrogen-atom Hamiltonian"; tap **Show Answer** to
see the formula typeset by MathJax, then grade Again/Hard/Good/Easy. Back returns
to the deck list (counts refresh). Use **"+"** to **create** a new empty deck or
**import** one of the bundled PGRE subject decks.

To take a screenshot of the running simulator:

```bash
xcrun simctl io booted screenshot speedrun.png
```

---

## 3'. iOS device build (unsigned `.ipa` for sideloading)

The Simulator build above runs `arm64` for the **simulator** SDK. To run on a
**physical iPhone** you need a real `iphoneos` build. Because there's **no Apple
Developer account** on the build machine, it's produced **unsigned** and
sideloaded (re-signed) on the user's own Apple ID.

### 3'a. Build the Rust core for the device

The `mobile/build-xcframework.sh` step from §2a already compiles the
`aarch64-apple-ios` (device) slice into `mobile/AnkiCore.xcframework`, so the same
xcframework covers both Simulator and device — no separate core build needed.

### 3'b. Build the app for the device SDK (unsigned)

```bash
xcodebuild \
  -project mobile/SpeedrunApp/SpeedrunApp.xcodeproj \
  -scheme SpeedrunApp \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath out/ios-device \
  CODE_SIGNING_ALLOWED=NO \
  build
```

`CODE_SIGNING_ALLOWED=NO` skips code signing (no Developer ID/team required). The
result is a real `arm64` `platform IOS` Mach-O (min iOS 15).

### 3'c. Package it into a `.ipa`

An `.ipa` is just a zip with the `.app` under a top-level `Payload/` folder:

```bash
APP=out/ios-device/Build/Products/Release-iphoneos/SpeedrunApp.app
rm -rf out/ios-device/Payload && mkdir -p out/ios-device/Payload
cp -R "$APP" out/ios-device/Payload/
(cd out/ios-device && zip -qry SpeedrunApp-iOS-device-unsigned.ipa Payload)
cp out/ios-device/SpeedrunApp-iOS-device-unsigned.ipa \
   installers/SpeedrunApp-iOS-device-unsigned.ipa
```

Artifact (~22 MB), bundle id `net.ankiweb.speedrun`, PGRE deck bundled:

```
installers/SpeedrunApp-iOS-device-unsigned.ipa
```

### Install it on a phone (sideload)

The `.ipa` is **UNSIGNED**, so it can't be installed as-is — it must be **re-signed
with your own Apple ID**. Use a sideloading tool:

- **[Sideloadly](https://sideloadly.io)** or **[AltStore](https://altstore.io)** —
  plug in the iPhone, drop in the `.ipa`, sign in with a free Apple ID; it re-signs
  and installs. (Free-account apps expire after 7 days and must be re-installed.)
- Once an Apple Developer ID/team is available, the same project can instead be
  **exported signed** (set a team + `CODE_SIGN_IDENTITY` / provisioning profile).

> **Not on TestFlight.** TestFlight distribution requires a **paid** Apple
> Developer account, which the build machine doesn't have — hence the unsigned
> sideload `.ipa` rather than a TestFlight link.

---

## 4. (Optional) Run the test suites

```bash
export PATH="$HOME/.cargo/bin:$PATH"

# Full desktop gate (Rust + Python + TS lint & tests)
just check

# iOS UI tests on a booted simulator
xcodebuild \
  -project mobile/SpeedrunApp/SpeedrunApp.xcodeproj \
  -scheme SpeedrunApp -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  -derivedDataPath out/ios test
```

---

## Troubleshooting

- **`cargo: command not found`** during `./ninja` — Cargo isn't on `PATH`. Run
  `export PATH="$HOME/.cargo/bin:$PATH"` in the same shell.
- **`mac-template` / submodule errors** in the installer build — run
  `git submodule update --init --recursive`.
- **`xcodebuild` can't find a simulator** — `xcrun simctl list devices available`
  and boot one, or install more runtimes via Xcode ▸ Settings ▸ Components.
- **xcframework link errors** ("no such module CAnkiFFI" / missing arch) — re-run
  `mobile/build-xcframework.sh`; ensure both iOS Rust targets are installed
  (`rustup target list --installed | grep ios`).
- **A "SpeedrunAppUITests-Runner" icon appears / "breaks" when tapped** — that's
  the UI-**test** runner, installed on the simulator by `xcodebuild … test` (§4).
  It has no UI of its own and does nothing when tapped directly. Open the icon
  named **"Speedrun"** instead. Remove the runner with
  `xcrun simctl uninstall booted net.ankiweb.speedrun.uitests.xctrunner`. To
  avoid installing it at all, use the `build` command (§2b), not `test`.
- **Gatekeeper blocks Anki.app** — expected for an ad-hoc build; see §1 install.
- **Briefcase/SPM network failures** — the first build downloads dependencies;
  ensure you're online and retry.
