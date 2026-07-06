# Anki Code Map (navigation diagrams)

Purpose: let an agent locate the **exact file + function** for a feature without
reading the tree. Every node is labeled `role` + `path :: symbol`. Line numbers
(where shown) were verified at time of writing but **drift** — the _function/type
name is the stable anchor_; grep for it if the line is off.

See also: [docs/architecture.md](docs/architecture.md),
[docs/data-flow.md](docs/data-flow.md), [docs/rust-core.md](docs/rust-core.md).

---

## 0. Layer overview — where each language lives

```mermaid
flowchart TD
    subgraph FE["Frontend (TypeScript / Svelte) — ts/"]
        TS["pages: ts/routes/*<br/>transport: ts/lib/generated/post.ts :: postProto()"]
    end
    subgraph QT["Desktop GUI (PyQt) — qt/aqt/"]
        QTG["shell: qt/aqt/main.py<br/>web bridge: qt/aqt/webview.py<br/>http: qt/aqt/mediasrv.py :: handle_request()"]
    end
    subgraph PY["Python library — pylib/anki/"]
        PYL["API: pylib/anki/collection.py<br/>cmd: pylib/anki/_backend.py :: _run_command()"]
    end
    subgraph FFI["FFI hosts"]
        RB["PyO3: pylib/rsbridge/lib.rs :: command() / open_backend()"]
        IOS["iOS C-ABI: mobile/anki-ffi/ → AnkiCore.xcframework<br/>(aarch64-apple-ios-sim + aarch64-apple-ios device)"]
    end
    subgraph RS["Rust core — rslib/"]
        BK["dispatch: rslib/rust_interface.rs :: run_service_method()<br/>included by rslib/src/services.rs<br/>backend: rslib/src/backend/mod.rs"]
        SVC["per-domain impls: rslib/src/<module>/service.rs"]
        ST["storage: rslib/src/storage/ (SQLite)"]
    end
    DB[("collection.anki2<br/>SQLite")]
    PROTO["contract: proto/anki/*.proto"]

    TS -->|"HTTP POST /_anki/{method}"| QTG
    QTG --> PYL
    TS -.->|"protobuf bytes"| RB
    PYL --> RB
    RB --> BK
    IOS -.-> BK
    BK --> SVC --> ST --> DB
    PROTO -.->|"codegen drives all layers"| BK
    PROTO -.-> TS
    PROTO -.-> PYL
```

---

## 1. Cross-language request flow (follow one RPC end-to-end)

```mermaid
flowchart LR
    A["caller (Python)<br/>pylib/anki/collection.py"] --> B["generated stub<br/>out/pylib/anki/_backend_generated.py<br/>(from rslib/proto/python.rs)"]
    B --> C["pylib/anki/_backend.py :: _run_command(service, method, bytes)"]
    C --> D["FFI: pylib/rsbridge/lib.rs :: command()  L49"]
    D --> E["rslib/rust_interface.rs :: run_service_method(service, method, input)  L141<br/>(generated into services.rs)"]
    E --> F["rslib/src/backend/mod.rs :: with_col()  L116"]
    F --> G["trait impl: rslib/src/<module>/service.rs"]
    G --> H["storage: rslib/src/storage/*"]
    H --> G --> E -->|"protobuf bytes back"| C

    A2["caller (TypeScript)<br/>import from @generated/backend"] --> P["ts/lib/generated/post.ts :: postProto()  L9"]
    P -->|"POST /_anki/{method}"| M["qt/aqt/mediasrv.py :: handle_request()  L382"]
    M --> E

    DBX["raw SQL path:<br/>pylib/anki/_backend.py :: db_query()"] --> DBC["rslib/src/backend/mod.rs :: run_db_command_bytes()  L104<br/>impl rslib/src/backend/dbproxy.rs"]
    DBC --> H
```

---

## 2. rslib subsystem locator (the main "where is feature X?" map)

```mermaid
flowchart TD
    LIB["rslib/src/lib.rs (module roots)"]

    LIB --> COL["Collection state / open / undo / backup<br/>rslib/src/collection/mod.rs :: Collection, CollectionBuilder<br/>open RPC: rslib/src/backend/collection.rs :: open_collection() L17"]
    LIB --> STOR["SQLite storage (per-entity submodules)<br/>rslib/src/storage/ (card/ note/ deck/ revlog/ ...)<br/>migrations: rslib/src/storage/upgrades/ • integrity: rslib/src/dbcheck.rs"]
    LIB --> SCH["Scheduler + FSRS (see Diagram 3)<br/>rslib/src/scheduler/"]
    LIB --> SR["Search: string→AST→SQL (see Diagram 4)<br/>rslib/src/search/"]
    LIB --> CARD["Cards CRUD<br/>rslib/src/card/mod.rs :: Card, FsrsMemoryState (L106)<br/>rslib/src/card/service.rs"]
    LIB --> NOTE["Notes CRUD + tags-on-note<br/>rslib/src/notes/mod.rs :: Note.tags"]
    LIB --> NT["Note types / templates schema<br/>rslib/src/notetype/"]
    LIB --> DECK["Decks + tree + limits<br/>rslib/src/decks/ (tree.rs, limits.rs, name.rs)"]
    LIB --> DC["Deck config (FSRS params, retention)<br/>rslib/src/deckconfig/mod.rs :: fsrs_params() L112"]
    LIB --> REND["Card rendering pipeline<br/>rslib/src/template.rs • template_filters.rs • cloze.rs<br/>rslib/src/card_rendering/ (parser.rs, writer.rs)"]
    LIB --> IE["Import / Export<br/>rslib/src/import_export/package/ (.apkg/.colpkg)<br/>rslib/src/import_export/text/ (CSV)"]
    LIB --> MED["Media files + check + sync<br/>rslib/src/media/ (files.rs, check.rs)"]
    LIB --> SYNC["Sync (collection + media)<br/>rslib/src/sync/collection/ • media/ • http_client/ • http_server/"]
    LIB --> TAGS["Tags hierarchy<br/>rslib/src/tags/ • service.rs :: all_tags()"]
    LIB --> STATS["Stats / graphs data<br/>rslib/src/stats/"]
    LIB --> REV["Review log (answer latency!)<br/>rslib/src/revlog/mod.rs :: RevlogEntry.taken_millis (L57)"]
    LIB --> OPS["Operations + undo model<br/>rslib/src/ops.rs :: Op, OpChanges, StateChanges<br/>rslib/src/undo/ :: UndoManager"]
    LIB --> ERR["Errors<br/>rslib/src/error/mod.rs :: AnkiError<br/>→proto: rslib/src/backend/error.rs :: into_protobuf() L11"]
    LIB --> I18N["i18n (Fluent), generated from ftl/<br/>rslib/src/i18n/"]
    LIB --> BR["Browser table (retrievability display)<br/>rslib/src/browser_table.rs :: current_retrievability_seconds() L548"]
    LIB --> IO["Image occlusion<br/>rslib/src/image_occlusion/"]
```

---

## 3. Scheduler, FSRS & latency (most relevant to Speedrun)

```mermaid
flowchart TD
    Q["Get next/queued cards<br/>proto: scheduler.proto :: GetQueuedCards<br/>impl: rslib/src/scheduler/queue/mod.rs :: get_queued_cards() L88"]
    AserviceQ["service entry: rslib/src/scheduler/service/mod.rs"]
    A["Answer a card (writes revlog + reschedules)<br/>proto: scheduler.proto :: AnswerCard / CardAnswer<br/>service: rslib/src/scheduler/service/mod.rs :: answer_card() L232<br/>core: rslib/src/scheduler/answering/mod.rs :: answer_card() L311"]
    STATES["Next-state math (FSRS/SM2)<br/>rslib/src/scheduler/states/ (review.rs, learning.rs, ...)"]
    MS["Compute memory state (stability/difficulty)<br/>rslib/src/scheduler/fsrs/memory_state.rs :: compute_memory_state() L360"]
    MEM["Card memory state type<br/>rslib/src/card/mod.rs :: FsrsMemoryState (stability, difficulty) L106"]
    RET["Current recall probability R<br/>fsrs crate :: current_retrievability_seconds(state, secs, decay)<br/>call site: rslib/src/browser_table.rs L548<br/>elapsed: card.seconds_since_last_review(&timing)<br/>decay: rslib/src/scheduler/fsrs/memory_state.rs :: get_decay_from_params() L37"]
    REVLOG["Per-answer latency<br/>rslib/src/revlog/mod.rs :: RevlogEntry.taken_millis L57<br/>(client supplies milliseconds_taken on CardAnswer)"]
    FSRSON["Is FSRS enabled?<br/>get_config_bool(BoolKey::Fsrs) + deckconfig fsrs_params non-empty"]
    TIMING["'now' / day rollover<br/>rslib/src/scheduler/mod.rs :: timing_today() L50"]

    AserviceQ --> Q
    AserviceQ --> A
    A --> STATES --> MEM
    A --> REVLOG
    MS --> MEM
    MEM --> RET
    FSRSON --> MS
    TIMING --> RET
```

---

## 4. Search pipeline (string → results)

```mermaid
flowchart LR
    IN["query string e.g. 'tag:pgre::classical_mechanics'"] --> PARSE["rslib/src/search/parser.rs (string → AST)"]
    PARSE --> WRITE["rslib/src/search/sqlwriter.rs (AST → SQL)"]
    WRITE --> RUN["rslib/src/search/mod.rs :: search_cards() / search_notes()"]
    BUILD["programmatic builder<br/>rslib/src/search/builder.rs :: from_tag_name() L175"] --> WRITE
    SVC["RPC: rslib/src/search/service.rs"] --> RUN
```

---

## 5. Frontend (TypeScript / Svelte) — page locator

```mermaid
flowchart TD
    ROUTES["ts/routes/ (SvelteKit pages)"]
    ROUTES --> DO["Deck options / scheduling UI<br/>ts/routes/deck-options/ (lib.ts = state, +page.svelte)"]
    ROUTES --> GR["Stats graphs (D3)<br/>ts/routes/graphs/"]
    ROUTES --> CI["Card info<br/>ts/routes/card-info/"]
    ROUTES --> CN["Change note type<br/>ts/routes/change-notetype/"]
    ROUTES --> IMP["Importers<br/>ts/routes/import-csv/ • import-anki-package/ • import-page/"]
    ROUTES --> IOCC["Image occlusion editor<br/>ts/routes/image-occlusion/"]
    ROUTES --> CG["Congrats / end-of-session<br/>ts/routes/congrats/"]

    EDIT["Rich editor (not a route)<br/>ts/editor/ :: NoteEditor.svelte"]
    REVU["Reviewer JS<br/>ts/reviewer/index.ts :: answering.ts"]
    LIBC["Shared components<br/>ts/lib/components/ • ts/lib/sveltelib/ • ts/lib/domlib/"]
    POST["Backend transport<br/>ts/lib/generated/post.ts :: postProto() L9<br/>(call via: import from @generated/backend)"]

    DO --> POST
    GR --> POST
```

---

## 6. Qt desktop GUI — component locator

```mermaid
flowchart TD
    MAIN["App shell / main window / state<br/>qt/aqt/main.py :: AnkiQt<br/>landing state = 'manifold' (Speedrun)"]
    MAIN --> MSRV["Local HTTP server (serves pages + RPC)<br/>qt/aqt/mediasrv.py :: handle_request() L382"]
    MAIN --> WV["WebView bridge (pycmd / web.eval)<br/>qt/aqt/webview.py :: AnkiWebView"]
    MAIN --> MAN["🟩 Manifold home screen (Speedrun landing)<br/>qt/aqt/manifold.py :: Manifold<br/>HTML: qt/aqt/pgre.py :: build_manifold_html()"]
    MAIN --> REV["Reviewer screen<br/>qt/aqt/reviewer.py :: Reviewer"]
    MAIN --> DB2["Classic deck list (reachable from manifold)<br/>qt/aqt/deckbrowser.py :: DeckBrowser"]
    MAIN --> BROW["Card browser<br/>qt/aqt/browser/browser.py :: Browser"]
    MAIN --> ED["Editor host<br/>qt/aqt/editor.py :: Editor"]
    MAIN --> DOPT["Deck options dialog (hosts Svelte page)<br/>qt/aqt/deckoptions.py"]
    MAIN --> SEED["🟩 First-run default-deck seeder<br/>qt/aqt/pgre.py :: import_default_decks() /<br/>maybe_import_default_decks()"]
    MAIN --> OPS["Undoable GUI operations<br/>qt/aqt/operations/"]
    WV --> MSRV
    MAN --> WV
    DOPT --> WV
    REV --> WV
```

The Speedrun fork replaces the deck list as the landing screen with a
**Calabi-Yau manifold home screen** ([qt/aqt/manifold.py](qt/aqt/manifold.py),
modeled on `qt/aqt/deckbrowser.py`). `AnkiQt` gains a `"manifold"`
`MainWindowState` plus `setupManifold()` / `_manifoldState()`, and
`loadCollection` calls `moveToState("manifold")`. The screen renders
`qt/aqt/data/web/imgs/calabi-yau.jpg` with a button at each of the manifold's 10
outer points: the first 9 are the PGRE subjects (clicking runs
`pycmd('open:<deckId>')` → the deck's "Study Now" overview), the 10th is a
"Coming soon" placeholder, and a "Classic deck list" link (`pycmd('classic')`)
opens the intact `DeckBrowser`. The toolbar "Decks" link, the `d` shortcut, the
overview "Decks" back-link, and the reviewer "Finish" action all return to
`"manifold"`. On first launch of a fresh collection, `_seed_default_decks`
auto-imports the 9 bundled PGRE decks (see Diagram 7 / the taxonomy note).

---

## 7. Build & generated code (where the missing files come from)

```mermaid
flowchart LR
    PROTO["proto/anki/*.proto"] --> GEN["rslib/proto/{rust.rs, python.rs, typescript.rs}<br/>+ rslib/proto_gen/ :: get_services()"]
    GEN --> ROUT["$OUT_DIR/backend.rs (Rust traits + dispatch)<br/>← rslib/rust_interface.rs"]
    GEN --> POUT["out/pylib/anki/_backend_generated.py + *_pb2.py"]
    GEN --> TOUT["out/ts/lib/generated/ (@generated/backend, @generated/anki/*_pb)"]
    FTL["ftl/*.ftl"] --> I18NGEN["rslib/src/i18n/ → generated tr APIs (Rust/TS/Py)"]
    JUST["justfile (just run / check / test-*)"] --> NG["build/ninja_gen → build.ninja → ninja/n2"]
```

---

## 8. Speedrun additions — where the fork's code lives (shipped)

From [PRD.md](PRD.md) / [SPECS.md](SPECS.md). These files now **exist** (the
diagram originally listed them as planned target locations).

```mermaid
flowchart TD
    NPROTO["proto/anki/speedrun.proto :: SpeedrunService.TopicMastery"]
    NMOD["rslib/src/speedrun/{mod.rs, service.rs}<br/>reuses: search_cards, FsrsMemoryState, current_retrievability_seconds, revlog.taken_millis"]
    REG["register: rslib/src/lib.rs (pub mod speedrun) + dispatch"]
    NPY["pylib/anki/speedrun.py wrapper"]
    NTS["ts/routes/speedrun-dashboard/ (Svelte page)"]
    NFFI["mobile/anki-ffi/ (staticlib C-ABI) → AnkiCore.xcframework<br/>(sim + device slices; device slice → unsigned .ipa, see BUILD_INSTALLERS.md §3')"]
    NIOS["mobile/SpeedrunApp/ (SwiftUI app)<br/>AI grader: HeuristicCoach.swift"]
    NCOACH["AI Heuristic Coach (MCQ grader)<br/>desktop: qt/aqt/heuristic_coach.py (used by qt/aqt/pgre.py)<br/>iOS: mobile/SpeedrunApp/.../HeuristicCoach.swift"]

    NPROTO --> NMOD --> REG
    NMOD --> NPY --> NTS
    NFFI --> NIOS
    NMOD -.->|"same RPC, two hosts"| NFFI
    NIOS -.-> NCOACH
```

---

## 9. Feature → file/function index (fallback lookup)

| Feature                            | File :: symbol                                                                                                                                                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RPC dispatch (service,method→impl) | `rslib/rust_interface.rs :: run_service_method` (gen → `rslib/src/services.rs`)                                                                                                                          |
| Backend init / collection lock     | `rslib/src/backend/mod.rs :: init_backend` (L69), `with_col` (L116)                                                                                                                                      |
| Raw SQL proxy                      | `rslib/src/backend/mod.rs :: run_db_command_bytes` (L104) → `backend/dbproxy.rs`                                                                                                                         |
| Open a collection                  | `rslib/src/backend/collection.rs :: open_collection` (L17)                                                                                                                                               |
| Python→Rust FFI                    | `pylib/rsbridge/lib.rs :: command` (L49) / `open_backend` (L40)                                                                                                                                          |
| Python command entry               | `pylib/anki/_backend.py :: _run_command` (L159)                                                                                                                                                          |
| TS→Rust transport                  | `ts/lib/generated/post.ts :: postProto` (L9) → `qt/aqt/mediasrv.py :: handle_request` (L382)                                                                                                             |
| Get next cards to review           | `rslib/src/scheduler/queue/mod.rs :: get_queued_cards` (L88)                                                                                                                                             |
| Answer a card                      | `rslib/src/scheduler/answering/mod.rs :: answer_card` (L311); service `scheduler/service/mod.rs :: answer_card` (L232)                                                                                   |
| Answer latency (speed signal)      | `rslib/src/revlog/mod.rs :: RevlogEntry.taken_millis` (L57)                                                                                                                                              |
| FSRS memory state (type)           | `rslib/src/card/mod.rs :: FsrsMemoryState` (L106)                                                                                                                                                        |
| Compute memory state               | `rslib/src/scheduler/fsrs/memory_state.rs :: compute_memory_state` (L360)                                                                                                                                |
| Current recall probability R       | `fsrs` crate `current_retrievability_seconds`; call site `rslib/src/browser_table.rs` (L548)                                                                                                             |
| FSRS decay selection               | `rslib/src/scheduler/fsrs/memory_state.rs :: get_decay_from_params` (L37)                                                                                                                                |
| Deck FSRS params / retention       | `rslib/src/deckconfig/mod.rs :: fsrs_params` (L112)                                                                                                                                                      |
| Tag search builder                 | `rslib/src/search/builder.rs :: from_tag_name` (L175)                                                                                                                                                    |
| Search parse / SQL                 | `rslib/src/search/parser.rs`, `sqlwriter.rs`, run via `search/mod.rs :: search_cards`                                                                                                                    |
| Note tags storage                  | `rslib/src/notes/mod.rs :: Note.tags`; all tags `rslib/src/tags/service.rs :: all_tags`                                                                                                                  |
| Undo / change tracking             | `rslib/src/ops.rs :: Op/OpChanges/StateChanges`; `rslib/src/undo/ :: UndoManager`                                                                                                                        |
| Error → protobuf                   | `rslib/src/backend/error.rs :: into_protobuf` (L11); `rslib/src/error/mod.rs :: AnkiError`                                                                                                               |
| "now" / day rollover               | `rslib/src/scheduler/mod.rs :: timing_today` (L50)                                                                                                                                                       |
| Card render / templates            | `rslib/src/template.rs`, `cloze.rs`, `card_rendering/`                                                                                                                                                   |
| Import/export (.apkg/CSV)          | `rslib/src/import_export/package/`, `import_export/text/`                                                                                                                                                |
| Sync (collection/media)            | `rslib/src/sync/{collection,media,http_client,http_server}/`                                                                                                                                             |
| Reviewer UI (desktop)              | `qt/aqt/reviewer.py :: Reviewer`; web `ts/reviewer/index.ts`                                                                                                                                             |
| Manifold home screen (Speedrun)    | `qt/aqt/manifold.py :: Manifold`; HTML `qt/aqt/pgre.py :: build_manifold_html`; state `qt/aqt/main.py :: "manifold"` (`setupManifold`/`_manifoldState`)                                                  |
| AI Heuristic Coach (MCQ grader)    | desktop `qt/aqt/heuristic_coach.py` (used by `qt/aqt/pgre.py`); iOS `mobile/SpeedrunApp/Sources/HeuristicCoach.swift`                                                                                    |
| iOS C-FFI / xcframework / device   | `mobile/anki-ffi/` → `mobile/AnkiCore.xcframework` (sim + `aarch64-apple-ios` device); unsigned `.ipa` per `BUILD_INSTALLERS.md` §3'                                                                     |
| First-run default-deck import      | `qt/aqt/pgre.py :: import_default_decks`/`maybe_import_default_decks` (flag `pgreDefaultDecksImported`); `qt/aqt/main.py :: _seed_default_decks`; build rule `build/configure/src/aqt.rs :: build_decks` |
| Test helpers (Rust)                | `rslib/src/tests.rs :: NoteAdder, CardAdder`; `Collection::new()`                                                                                                                                        |
| Test helpers (Python)              | `pylib/tests/shared.py :: getEmptyCol`; review via `col.sched.answerCard(card, ease)`                                                                                                                    |

```
```
