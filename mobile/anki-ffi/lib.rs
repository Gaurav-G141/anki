// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! A tiny C ABI around Anki's existing backend command interface.
//!
//! This crate mirrors `pylib/rsbridge`: it wraps
//! [`anki::backend::init_backend`]
//! and [`anki::backend::Backend::run_service_method`] so a host application
//! (e.g. an iOS app) can drive the exact same Rust engine over a stable C
//! boundary. It is intentionally minimal — four functions plus a last-error
//! accessor.
//!
//! # Protobuf contract
//!
//! All payloads crossing the boundary are protobuf-encoded bytes, identical to
//! what the Python/TypeScript clients exchange with the backend:
//!
//! * `anki_open_backend` takes an encoded `anki.backend.BackendInit`.
//! * `anki_command` takes the encoded request for the chosen service/method and
//!   returns either the encoded response (status 0) or an encoded
//!   `anki.backend.BackendError` (status 1).
//!
//! Service/method indices match the backend dispatch table generated from the
//! `.proto` files (see `run_service_method`). For example
//! `SpeedrunService.TopicMastery` is service 43, method 0, and
//! `CollectionService.OpenCollection` is service 3, method 0.
//!
//! # Threading
//!
//! The backend lazily builds a multi-threaded tokio runtime on first use, and
//! [`anki_command`] blocks the calling thread until the RPC completes. Callers
//! MUST therefore invoke `anki_command` off the platform's main/UI thread.
//!
//! # Memory ownership
//!
//! * The `*mut Backend` returned by [`anki_open_backend`] is owned by the
//!   caller and must be released exactly once with [`anki_close_backend`].
//! * The `*mut u8` buffer returned by [`anki_command`] is a heap allocation
//!   owned by the caller and must be released exactly once with [`anki_free`],
//!   passing back the same pointer and the `out_len` that was written. The
//!   buffer is produced via `Box<[u8]>::into_raw`, and [`anki_free`]
//!   reconstructs that boxed slice and drops it.

use std::cell::RefCell;
use std::ffi::c_char;
use std::ffi::CString;
use std::slice;

use anki::backend::init_backend;
use anki::backend::Backend;

thread_local! {
    /// Holds the most recent error message for the current thread, so a caller
    /// that received a null pointer can retrieve a human-readable reason.
    static LAST_ERROR: RefCell<Option<CString>> = const { RefCell::new(None) };
}

fn set_last_error(msg: impl Into<Vec<u8>>) {
    // Replace interior NULs so the CString construction never fails.
    let bytes: Vec<u8> = msg
        .into()
        .into_iter()
        .map(|b| if b == 0 { b' ' } else { b })
        .collect();
    let cstr = CString::new(bytes).unwrap_or_default();
    LAST_ERROR.with(|slot| *slot.borrow_mut() = Some(cstr));
}

/// Returns a pointer to a NUL-terminated string describing the most recent
/// error on the *current thread*, or null if there is none.
///
/// The returned pointer is owned by this crate's thread-local storage and is
/// valid until the next FFI call on the same thread. Callers must copy the
/// string if they need to retain it; they must NOT free it.
///
/// # Safety
///
/// The caller must not retain the pointer across subsequent FFI calls on the
/// same thread.
#[no_mangle]
pub extern "C" fn anki_last_error() -> *const c_char {
    LAST_ERROR.with(|slot| match slot.borrow().as_ref() {
        Some(cstr) => cstr.as_ptr(),
        None => std::ptr::null(),
    })
}

/// Decodes an `anki.backend.BackendInit` protobuf and opens a backend.
///
/// On success, returns an owned, non-null `*mut Backend` that must be released
/// with [`anki_close_backend`]. On failure, returns null and records a message
/// retrievable via [`anki_last_error`].
///
/// # Safety
///
/// `init_ptr` must either be null (treated as an empty `BackendInit`) or point
/// to at least `len` readable bytes.
#[no_mangle]
pub unsafe extern "C" fn anki_open_backend(init_ptr: *const u8, len: usize) -> *mut Backend {
    let init_bytes: &[u8] = if init_ptr.is_null() || len == 0 {
        &[]
    } else {
        // SAFETY: contract requires `init_ptr` to be valid for `len` bytes.
        unsafe { slice::from_raw_parts(init_ptr, len) }
    };

    match init_backend(init_bytes) {
        Ok(backend) => Box::into_raw(Box::new(backend)),
        Err(e) => {
            set_last_error(e);
            std::ptr::null_mut()
        }
    }
}

/// Runs a backend service method, mirroring `rsbridge`'s `command`.
///
/// On success writes `*status = 0` and returns a heap buffer holding the
/// encoded protobuf response. On a backend error writes `*status = 1` and
/// returns a heap buffer holding the encoded `anki.backend.BackendError`. On a
/// usage error (e.g. null backend) writes `*status = -1`, records a message in
/// [`anki_last_error`], and returns null.
///
/// In all non-null return cases `*out_len` is set to the buffer length and the
/// caller must release the buffer with [`anki_free`] using that same length.
///
/// Blocks the calling thread; see the module-level threading note.
///
/// # Safety
///
/// `be` must be a pointer returned by [`anki_open_backend`] that has not been
/// closed. `in_ptr` must be null or valid for `in_len` bytes. `out_len` and
/// `status` must be valid, writable pointers.
#[no_mangle]
pub unsafe extern "C" fn anki_command(
    be: *mut Backend,
    service: u32,
    method: u32,
    in_ptr: *const u8,
    in_len: usize,
    out_len: *mut usize,
    status: *mut i32,
) -> *mut u8 {
    if out_len.is_null() || status.is_null() {
        // Nowhere safe to report; bail out without touching the null pointers.
        return std::ptr::null_mut();
    }
    // SAFETY: checked non-null above.
    unsafe {
        *out_len = 0;
        *status = -1;
    }

    if be.is_null() {
        set_last_error("anki_command called with null backend");
        return std::ptr::null_mut();
    }

    // SAFETY: contract requires a live backend pointer; we only borrow it.
    let backend: &Backend = unsafe { &*be };

    let input: &[u8] = if in_ptr.is_null() || in_len == 0 {
        &[]
    } else {
        // SAFETY: contract requires `in_ptr` valid for `in_len` bytes.
        unsafe { slice::from_raw_parts(in_ptr, in_len) }
    };

    let (bytes, code) = match backend.run_service_method(service, method, input) {
        Ok(out) => (out, 0i32),
        Err(err) => (err, 1i32),
    };

    // SAFETY: checked non-null above.
    unsafe {
        *status = code;
    }
    into_raw_buffer(bytes, out_len)
}

/// Converts an owned byte vector into a raw heap buffer, writing its length to
/// `out_len`. Returns null for an empty buffer (length 0).
fn into_raw_buffer(bytes: Vec<u8>, out_len: *mut usize) -> *mut u8 {
    let boxed: Box<[u8]> = bytes.into_boxed_slice();
    let len = boxed.len();
    // SAFETY: `out_len` checked non-null by the sole caller.
    unsafe {
        *out_len = len;
    }
    if len == 0 {
        // An empty (but successful) response: no allocation to hand back.
        return std::ptr::null_mut();
    }
    Box::into_raw(boxed) as *mut u8
}

/// Releases a buffer previously returned by [`anki_command`].
///
/// # Safety
///
/// `ptr`/`len` must be exactly the pointer and length produced by a single
/// [`anki_command`] call, and must not be freed more than once. A null `ptr`
/// (the empty-response case) is a no-op.
#[no_mangle]
pub unsafe extern "C" fn anki_free(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    // SAFETY: reconstruct the exact boxed slice produced by `into_raw_buffer`.
    unsafe {
        let slice = slice::from_raw_parts_mut(ptr, len);
        drop(Box::from_raw(slice as *mut [u8]));
    }
}

/// Closes a backend previously opened by [`anki_open_backend`].
///
/// # Safety
///
/// `be` must be a pointer returned by [`anki_open_backend`] that has not
/// already been closed. A null pointer is a no-op.
#[no_mangle]
pub unsafe extern "C" fn anki_close_backend(be: *mut Backend) {
    if be.is_null() {
        return;
    }
    // SAFETY: reconstruct the Box created in `anki_open_backend` and drop it.
    unsafe {
        drop(Box::from_raw(be));
    }
}

#[cfg(test)]
mod tests {
    use std::ffi::CStr;

    use anki_proto::collection::OpenCollectionRequest;
    use anki_proto::speedrun::TopicMasteryResponse;
    use prost::Message;

    use super::*;

    // Service/method indices from the generated backend dispatch table
    // (out/.../backend.rs `Backend::run_service_method`). The `Backend` struct
    // dispatches the odd-indexed "Backend*" services.
    const SVC_COLLECTION: u32 = 3;
    const M_OPEN_COLLECTION: u32 = 0;
    const SVC_SPEEDRUN: u32 = 43;
    const M_TOPIC_MASTERY: u32 = 0;

    /// Opens a backend from an empty `BackendInit` (preferred_langs=[]).
    fn open() -> *mut Backend {
        // An empty BackendInit encodes to zero bytes; pass null/0.
        let be = unsafe { anki_open_backend(std::ptr::null(), 0) };
        assert!(!be.is_null(), "anki_open_backend returned null");
        be
    }

    /// Calls a service method and returns (status, response bytes).
    fn command(be: *mut Backend, service: u32, method: u32, input: &[u8]) -> (i32, Vec<u8>) {
        let mut out_len: usize = 0;
        let mut status: i32 = -99;
        let ptr = unsafe {
            anki_command(
                be,
                service,
                method,
                input.as_ptr(),
                input.len(),
                &mut out_len,
                &mut status,
            )
        };
        let bytes = if ptr.is_null() {
            Vec::new()
        } else {
            let copy = unsafe { slice::from_raw_parts(ptr, out_len) }.to_vec();
            unsafe { anki_free(ptr, out_len) };
            copy
        };
        (status, bytes)
    }

    fn topic_mastery(be: *mut Backend) -> (i32, Vec<u8>) {
        // Empty TopicMasteryRequest -> documented defaults.
        command(be, SVC_SPEEDRUN, M_TOPIC_MASTERY, &[])
    }

    /// S6-T02: round-trip through the C ABI on an in-memory collection and
    /// assert the speedrun response decodes with 9 topics and abstain==true.
    #[test]
    fn s6_t02_round_trip() {
        let be = open();

        // Open an in-memory collection so the collection-scoped speedrun
        // service has something to run against.
        let req = OpenCollectionRequest {
            collection_path: ":memory:".into(),
            media_folder_path: String::new(),
            media_db_path: String::new(),
        };
        let (status, _) = command(be, SVC_COLLECTION, M_OPEN_COLLECTION, &req.encode_to_vec());
        assert_eq!(status, 0, "open_collection should succeed");

        let (status, bytes) = topic_mastery(be);
        assert_eq!(status, 0, "topic_mastery should succeed");
        let resp = TopicMasteryResponse::decode(bytes.as_slice())
            .expect("response should decode as TopicMasteryResponse");

        assert_eq!(
            resp.topics.len(),
            9,
            "expected 9 topics, got {}",
            resp.topics.len()
        );
        assert!(resp.abstain, "empty collection should abstain");

        unsafe { anki_close_backend(be) };
    }

    /// S6-T04: the `anki` crate linked into this FFI crate must be the same
    /// engine the desktop build used. We assert `buildhash()` matches the hash
    /// recorded in out/buildhash. If that file is absent (clean checkout), we
    /// fall back to asserting the hash is non-empty, which still proves the
    /// `anki` crate is linked and exporting its version.
    #[test]
    fn s6_t04_engine_parity() {
        let linked = anki::version::buildhash();
        assert!(!linked.is_empty(), "buildhash should be populated");

        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../out/buildhash");
        match std::fs::read_to_string(path) {
            Ok(desktop) => {
                let desktop = desktop.trim();
                assert_eq!(
                    linked, desktop,
                    "FFI-linked buildhash {linked:?} != desktop buildhash {desktop:?}"
                );
            }
            Err(_) => {
                eprintln!("out/buildhash missing; asserted non-empty linked hash {linked:?}");
            }
        }
    }

    /// S6-T05: open a collection from an on-disk fixture (the FIX-SMALL
    /// speedrun fixture when present, else a fresh temp collection) and run
    /// topic_mastery, asserting the response decodes.
    #[test]
    fn s6_t05_open_and_query() {
        let be = open();

        // Prefer the prebuilt fixture; copy it so the test never mutates it.
        let fixture = concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../out/speedrun/work/pgre_main.anki2"
        );
        let tmp = tempfile::tempdir().unwrap();
        let col_path = tmp.path().join("col.anki2");
        if std::path::Path::new(fixture).exists() {
            std::fs::copy(fixture, &col_path).unwrap();
        }
        // If the fixture is absent, an empty path string makes the backend
        // create a new collection at this location.

        let req = OpenCollectionRequest {
            collection_path: col_path.to_string_lossy().into_owned(),
            media_folder_path: tmp.path().join("media").to_string_lossy().into_owned(),
            media_db_path: tmp.path().join("media.db").to_string_lossy().into_owned(),
        };
        let (status, _) = command(be, SVC_COLLECTION, M_OPEN_COLLECTION, &req.encode_to_vec());
        assert_eq!(status, 0, "open_collection from disk should succeed");

        let (status, bytes) = topic_mastery(be);
        assert_eq!(status, 0, "topic_mastery should succeed");
        let resp = TopicMasteryResponse::decode(bytes.as_slice()).expect("response should decode");
        // The fixture has 9 exam topics defined regardless of card content.
        assert_eq!(resp.topics.len(), 9, "expected 9 topics");

        unsafe { anki_close_backend(be) };
    }

    /// S6-T03: stress the round-trip many times to surface use-after-free or
    /// leaks. Run with a sanitizer for a deeper check, e.g. on nightly:
    ///   RUSTFLAGS="-Zsanitizer=address" cargo +nightly test -p anki-ffi \
    ///     --target aarch64-apple-darwin s6_t03
    #[test]
    fn s6_t03_memory_safety_loop() {
        let be = open();
        let req = OpenCollectionRequest {
            collection_path: ":memory:".into(),
            media_folder_path: String::new(),
            media_db_path: String::new(),
        };
        let (status, _) = command(be, SVC_COLLECTION, M_OPEN_COLLECTION, &req.encode_to_vec());
        assert_eq!(status, 0);

        for i in 0..10_000 {
            let (status, bytes) = topic_mastery(be);
            assert_eq!(status, 0, "iteration {i} failed");
            assert!(!bytes.is_empty(), "iteration {i} returned empty response");
        }
        unsafe { anki_close_backend(be) };
    }

    /// Sanity: a null backend yields status -1 and a retrievable error.
    #[test]
    fn null_backend_is_guarded() {
        let mut out_len: usize = 1;
        let mut status: i32 = 99;
        let ptr = unsafe {
            anki_command(
                std::ptr::null_mut(),
                SVC_SPEEDRUN,
                M_TOPIC_MASTERY,
                std::ptr::null(),
                0,
                &mut out_len,
                &mut status,
            )
        };
        assert!(ptr.is_null());
        assert_eq!(status, -1);
        assert_eq!(out_len, 0);
        let err = anki_last_error();
        assert!(!err.is_null());
        let msg = unsafe { CStr::from_ptr(err) }.to_string_lossy();
        assert!(msg.contains("null backend"), "got: {msg}");
    }

    /// Sanity: an invalid service index is reported as a backend error (status
    /// 1) carrying a decodable BackendError, not a crash.
    #[test]
    fn invalid_service_returns_backend_error() {
        let be = open();
        let (status, bytes) = command(be, 9999, 0, &[]);
        assert_eq!(status, 1);
        let err = anki_proto::backend::BackendError::decode(bytes.as_slice())
            .expect("should decode as BackendError");
        assert!(!err.message.is_empty());
        unsafe { anki_close_backend(be) };
    }
}
