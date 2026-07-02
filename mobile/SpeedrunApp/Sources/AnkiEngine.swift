// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
//
// Thin Swift wrapper over the C FFI exposed by mobile/AnkiCore.xcframework
// (anki_ffi.h). All calls into the engine block on a lazy tokio runtime, so the
// FFI documentation requires they be made *off the main thread*. `AnkiEngine`
// is therefore intended to be driven from a background queue / detached Task.

import CAnkiFFI
import Foundation
import SwiftProtobuf

/// Service/method indices into `Backend::run_service_method`, taken from the
/// generated dispatch table (out/.../backend.rs) and cross-checked against the
/// Python `out/pylib/anki/_backend_generated.py` `_run_command(service, method)`
/// calls:
///
///   * OpenCollection      -> service 3,  method 0  (BackendCollectionService)
///   * GetQueuedCards      -> service 13, method 3  (Scheduler, merged dispatch)
///   * AnswerCard          -> service 13, method 4  (Scheduler, merged dispatch)
///   * RenderExistingCard  -> service 27, method 6  (CardRendering, merged)
///   * DeckTree/NewDeck/AddDeck/SetCurrentDeck -> service 7 (Decks)
///   * SyncLogin/SyncCollection/FullUploadOrDownload -> service 1 (Sync)
///   * ImportAnkiPackage   -> service 39, method 2 (ImportExport)
enum AnkiService {
    static let sync: UInt32 = 1
    static let collection: UInt32 = 3
    static let decks: UInt32 = 7
    static let scheduler: UInt32 = 13
    static let cardRendering: UInt32 = 27
    static let importExport: UInt32 = 39
}

enum AnkiMethod {
    static let openCollection: UInt32 = 0
    static let closeCollection: UInt32 = 1
    static let getQueuedCards: UInt32 = 3
    static let answerCard: UInt32 = 4
    static let renderExistingCard: UInt32 = 6
    // Decks service (7): method order from proto/anki/decks.proto.
    static let newDeck: UInt32 = 0
    static let addDeck: UInt32 = 1
    static let deckTree: UInt32 = 4
    static let setCurrentDeck: UInt32 = 22
    // Sync service (1): method order from proto/anki/sync.proto.
    static let syncLogin: UInt32 = 3
    static let syncStatus: UInt32 = 4
    static let syncCollection: UInt32 = 5
    static let fullUploadOrDownload: UInt32 = 6
    static let abortSync: UInt32 = 7
    // ImportExport service (39).
    static let importAnkiPackage: UInt32 = 2
}

enum AnkiEngineError: Error, CustomStringConvertible {
    /// `anki_open_backend` returned null.
    case openBackendFailed(String)
    /// A usage error from `anki_command` (status -1).
    case usageError(String)
    /// The backend returned a `BackendError` proto (status 1).
    case backendError(message: String)
    /// Protobuf encode/decode failure on the Swift side.
    case codec(String)

    var description: String {
        switch self {
        case let .openBackendFailed(m): return "open backend failed: \(m)"
        case let .usageError(m): return "usage error: \(m)"
        case let .backendError(m): return "backend error: \(m)"
        case let .codec(m): return "codec error: \(m)"
        }
    }
}

/// Owns a single `*mut AnkiBackend`. Not thread-safe for concurrent commands;
/// the app serializes all access through one background queue.
final class AnkiEngine {
    private let handle: OpaquePointer

    private init(handle: OpaquePointer) {
        self.handle = handle
    }

    deinit {
        anki_close_backend(handle)
    }

    /// Opens a backend from a `BackendInit` proto.
    static func open(init initProto: Anki_Backend_BackendInit) throws -> AnkiEngine {
        let bytes = try initProto.serializedData()
        let handle: OpaquePointer? = bytes.withUnsafeBytes { raw -> OpaquePointer? in
            let base = raw.bindMemory(to: UInt8.self).baseAddress
            return anki_open_backend(base, UInt(bytes.count))
        }
        guard let handle else {
            throw AnkiEngineError.openBackendFailed(Self.lastError())
        }
        return AnkiEngine(handle: handle)
    }

    /// Reads the most recent thread-local error string from the FFI.
    static func lastError() -> String {
        guard let cstr = anki_last_error() else { return "(no error message)" }
        return String(cString: cstr)
    }

    /// Calls a service method with a request proto, decoding the typed response.
    func command<Req: SwiftProtobuf.Message, Resp: SwiftProtobuf.Message>(
        service: UInt32,
        method: UInt32,
        request: Req,
        response _: Resp.Type
    ) throws -> Resp {
        let raw = try commandRaw(service: service, method: method, input: try request.serializedData())
        do {
            return try Resp(serializedBytes: raw)
        } catch {
            throw AnkiEngineError.codec("failed to decode response: \(error)")
        }
    }

    /// Calls a service method with raw request bytes, returning raw response
    /// bytes. Throws `AnkiEngineError` on usage/backend errors.
    func commandRaw(service: UInt32, method: UInt32, input: Data) throws -> Data {
        var outLen: UInt = 0
        var status: Int32 = 0

        let resultPtr: UnsafeMutablePointer<UInt8>? = input.withUnsafeBytes { raw in
            let base = raw.bindMemory(to: UInt8.self).baseAddress
            return anki_command(
                handle, service, method, base, UInt(input.count), &outLen, &status
            )
        }

        // Usage error: null pointer, message in anki_last_error.
        if status == -1 {
            throw AnkiEngineError.usageError(Self.lastError())
        }

        // Copy out and free the Rust-owned buffer.
        var bytes = Data()
        if let resultPtr, outLen > 0 {
            bytes = Data(bytes: resultPtr, count: Int(outLen))
        }
        if let resultPtr {
            anki_free(resultPtr, outLen)
        }

        if status == 1 {
            // Payload is an encoded BackendError proto.
            let msg = (try? Anki_Backend_BackendError(serializedBytes: bytes))?.message
                ?? "(unparseable BackendError)"
            throw AnkiEngineError.backendError(message: msg)
        }

        return bytes
    }
}
