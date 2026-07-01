# The Rust Core (rslib)

`rslib/` holds the majority of Anki's backend logic: the collection model,
storage, scheduler, search, sync, import/export, and the rendering pipeline.
This document is a **map** so contributors can find the right module quickly; it
is not a substitute for the per-item API docs (`cargo doc`, see
[api-rust.md](./api-rust.md)).

For how this core is _reached_ from Python and TypeScript at runtime, read
[data-flow.md](./data-flow.md). For how to add a new RPC, read
[language_bridge.md](./language_bridge.md).

## Entry points

- [rslib/src/lib.rs](../rslib/src/lib.rs) declares every top-level module —
  it is the table of contents for the crate.
- [rslib/src/collection/mod.rs](../rslib/src/collection/mod.rs) defines
  `Collection` (the open collection: storage handle, media paths, i18n, undo
  state) and `CollectionBuilder`, which configures and opens one.
- [rslib/src/backend/](../rslib/src/backend/) defines `Backend`, the top-level
  object exposed over the FFI/HTTP boundary. It owns an optional `Collection`
  behind a mutex plus cross-request state (sync handles, progress, the async
  runtime). `Backend::run_service_method` (generated) is the RPC dispatcher.
- [rslib/src/prelude.rs](../rslib/src/prelude.rs) is the common import bundle
  used throughout the crate.

### The `service.rs` convention

Each protobuf service is implemented in a `service.rs` file (or `service/`
directory) inside its module — e.g.
[rslib/src/notes/service.rs](../rslib/src/notes/service.rs),
[rslib/src/decks/service.rs](../rslib/src/decks/service.rs),
[rslib/src/scheduler/service/](../rslib/src/scheduler/service/). The traits
these files implement are generated from the `.proto` definitions; the
generated dispatcher is pulled in via
[rslib/src/services.rs](../rslib/src/services.rs).

## Subsystem reference

| Module                 | Path                                                                                                                                                                                                                         | Responsibility                                                                                                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `collection`           | [rslib/src/collection/](../rslib/src/collection/)                                                                                                                                                                            | Open collection state, transactions, backups, and the undo entry points.                                                                                                          |
| `storage`              | [rslib/src/storage/](../rslib/src/storage/)                                                                                                                                                                                  | SQLite abstraction (`SqliteStorage`) with per-entity submodules (`card/`, `note/`, `deck/`, `notetype/`, `revlog/`, `tag/`, …) and `upgrades/` for schema migrations (V11 → V18). |
| `scheduler`            | [rslib/src/scheduler/](../rslib/src/scheduler/)                                                                                                                                                                              | Card scheduling: `queue/` (new/learning/review queue building), `answering/`, `states/` (next-interval calculations), `fsrs/` (FSRS algorithm), `filtered/` (filtered decks).     |
| `search`               | [rslib/src/search/](../rslib/src/search/)                                                                                                                                                                                    | The search engine: `parser.rs` turns a query string into an AST, `sqlwriter.rs` lowers the AST to SQL.                                                                            |
| `card` / `notes`       | [rslib/src/card/](../rslib/src/card/), [rslib/src/notes/](../rslib/src/notes/)                                                                                                                                               | Core `Card` and `Note` data structures and CRUD operations.                                                                                                                       |
| `notetype`             | [rslib/src/notetype/](../rslib/src/notetype/)                                                                                                                                                                                | Note type (model) schema: fields, card templates, and their management.                                                                                                           |
| `decks` / `deckconfig` | [rslib/src/decks/](../rslib/src/decks/), [rslib/src/deckconfig/](../rslib/src/deckconfig/)                                                                                                                                   | Deck hierarchy (`tree.rs`, `name.rs`, `limits.rs`) and per-deck scheduling configuration.                                                                                         |
| Card rendering         | [rslib/src/template.rs](../rslib/src/template.rs), [rslib/src/template_filters.rs](../rslib/src/template_filters.rs), [rslib/src/cloze.rs](../rslib/src/cloze.rs), [rslib/src/card_rendering/](../rslib/src/card_rendering/) | The card template language, its filters, cloze expansion, and HTML generation.                                                                                                    |
| `import_export`        | [rslib/src/import_export/](../rslib/src/import_export/)                                                                                                                                                                      | `.apkg`/`.colpkg` handling (`package/`) and text/CSV import (`text/`).                                                                                                            |
| `media`                | [rslib/src/media/](../rslib/src/media/)                                                                                                                                                                                      | Media file storage, integrity checking (`check.rs`), and media sync.                                                                                                              |
| `sync`                 | [rslib/src/sync/](../rslib/src/sync/)                                                                                                                                                                                        | Collection and media sync: `collection/`, `media/`, `http_client/`, and the self-hostable `http_server/`.                                                                         |
| `tags`                 | [rslib/src/tags/](../rslib/src/tags/)                                                                                                                                                                                        | Tag hierarchy and management.                                                                                                                                                     |
| `stats`                | [rslib/src/stats/](../rslib/src/stats/)                                                                                                                                                                                      | Review statistics backing the graphs page.                                                                                                                                        |
| `image_occlusion`      | [rslib/src/image_occlusion/](../rslib/src/image_occlusion/)                                                                                                                                                                  | The image occlusion note type.                                                                                                                                                    |
| `config`               | [rslib/src/config/](../rslib/src/config/)                                                                                                                                                                                    | Collection-wide configuration storage.                                                                                                                                            |
| `ops` / `undo`         | [rslib/src/ops.rs](../rslib/src/ops.rs), [rslib/src/undo/](../rslib/src/undo/)                                                                                                                                               | The `Op`/`OpChanges`/`StateChanges` model and the `UndoManager` transaction log (see [data-flow.md](./data-flow.md)).                                                             |
| `error`                | [rslib/src/error/](../rslib/src/error/)                                                                                                                                                                                      | `AnkiError`/`Result` and conversion to protobuf errors.                                                                                                                           |
| `i18n`                 | [rslib/src/i18n/](../rslib/src/i18n/)                                                                                                                                                                                        | Fluent-based translations; the type-safe API is generated from `ftl/`.                                                                                                            |
| Integration shims      | [rslib/src/backend/ankiweb.rs](../rslib/src/backend/ankiweb.rs), [rslib/src/backend/ankidroid.rs](../rslib/src/backend/ankidroid.rs), [rslib/src/ankihub/](../rslib/src/ankihub/)                                            | Helpers specific to AnkiWeb, AnkiDroid, and AnkiHub.                                                                                                                              |

Other notable single-file modules include
[rslib/src/browser_table.rs](../rslib/src/browser_table.rs) (data for the
browser's table view), [rslib/src/findreplace.rs](../rslib/src/findreplace.rs),
[rslib/src/latex.rs](../rslib/src/latex.rs),
[rslib/src/dbcheck.rs](../rslib/src/dbcheck.rs), and
[rslib/src/text.rs](../rslib/src/text.rs).

## Cross-cutting conventions

- **Error handling.** Inside `rslib`, use `error/mod.rs`'s `AnkiError`/`Result`
  with `snafu`. Other Rust crates in the repo prefer `anyhow` with added
  context. (See the project `CLAUDE.md`/`AGENTS.md`.)
- **IO and process helpers.** Prefer the helpers in
  [rslib/io/](../rslib/io/) and [rslib/process/](../rslib/process/) (exported as
  the `anki_io` crate, etc.) over raw `std` calls — they attach better error
  context and add ergonomics.
- **Transactions and undo.** Mutating operations run inside a transaction and
  return an `OpChanges` describing what changed, which feeds both UI refresh and
  undo. See [data-flow.md](./data-flow.md#operations-opchanges-and-undo).
- **Generated protobuf types.** Service methods take and return types from the
  generated `anki_proto` crate, built from `proto/anki/`. See
  [protobuf.md](./protobuf.md).

## Where generated code lives

Several files referenced here and in [data-flow.md](./data-flow.md) do not exist
until the project is built. They are written under `out/` and `$OUT_DIR`:

- `$OUT_DIR/backend.rs` — generated service traits and the
  `run_service_method` dispatcher, included by
  [rslib/src/services.rs](../rslib/src/services.rs).
- `out/pylib/anki/_backend_generated.py` — the generated Python `RustBackend`
  methods.
- `out/ts/lib/generated/` — the `@generated/backend` TypeScript wrappers.

You can inspect these after a build to see exactly how a given RPC is wired
across languages.
