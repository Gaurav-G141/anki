#!/usr/bin/env bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Builds the anki-ffi staticlib for the iOS device and simulator targets, emits
# the C header with cbindgen, and assembles mobile/AnkiCore.xcframework.
#
# Idempotent: re-running rebuilds and replaces existing artifacts. Requires a
# full Xcode install (xcodebuild) and the iOS Rust targets:
#   rustup target add aarch64-apple-ios aarch64-apple-ios-sim

set -euo pipefail

export PATH="$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CRATE_DIR="$SCRIPT_DIR/anki-ffi"
INCLUDE_DIR="$CRATE_DIR/include"
XCFRAMEWORK="$SCRIPT_DIR/AnkiCore.xcframework"

DEVICE_TARGET="aarch64-apple-ios"
SIM_TARGET="aarch64-apple-ios-sim"
LIB_NAME="libanki_ffi.a"

echo "==> Generating C header"
mkdir -p "$INCLUDE_DIR"
cbindgen --config "$CRATE_DIR/cbindgen.toml" \
    --output "$INCLUDE_DIR/anki_ffi.h" "$CRATE_DIR"

# We override the crate-type to `staticlib` only. The manifest also lists
# `cdylib` (handy for the host round-trip tests), but linking a cdylib for the
# iOS *device* target pulls in zstd's `___chkstk_darwin` and fails; the
# xcframework only needs the static archive, which doesn't link.
echo "==> Building staticlib for $SIM_TARGET (release)"
cargo rustc -p anki-ffi --target "$SIM_TARGET" --release --crate-type staticlib

echo "==> Building staticlib for $DEVICE_TARGET (release)"
cargo rustc -p anki-ffi --target "$DEVICE_TARGET" --release --crate-type staticlib

SIM_LIB="$REPO_ROOT/target/$SIM_TARGET/release/$LIB_NAME"
DEVICE_LIB="$REPO_ROOT/target/$DEVICE_TARGET/release/$LIB_NAME"

for lib in "$SIM_LIB" "$DEVICE_LIB"; do
    if [[ ! -f "$lib" ]]; then
        echo "ERROR: expected static library not found: $lib" >&2
        exit 1
    fi
done

echo "==> Assembling xcframework"
# xcodebuild refuses to overwrite an existing output directory.
rm -rf "$XCFRAMEWORK"
xcodebuild -create-xcframework \
    -library "$SIM_LIB" -headers "$INCLUDE_DIR" \
    -library "$DEVICE_LIB" -headers "$INCLUDE_DIR" \
    -output "$XCFRAMEWORK"

echo "==> Done: $XCFRAMEWORK"
ls -la "$XCFRAMEWORK"
