# Speedrun PGRE — System Architecture (visual)

A single visual synthesis of all the docs: the existing **Anki** engine
([CODE_MAP.md](CODE_MAP.md), [docs/tech-stack.md](docs/tech-stack.md),
[docs/data-flow.md](docs/data-flow.md), [docs/rust-core.md](docs/rust-core.md))
plus the planned **Speedrun** fork ([PRD.md](PRD.md), [SPECS.md](SPECS.md),
[speedrun/README.md](speedrun/README.md)).

> CODE_MAP.md is the canonical file→function locator. This doc is the
> bird's-eye view that stitches the architecture, data flow, and the Speedrun
> MVP plan into one picture.

**Legend** — 🟦 existing Anki · 🟩 NEW (Speedrun, planned) · 🟨 generated/build ·
⬜ data store.

---

## 1. The whole system — one engine, two apps, one new RPC

```mermaid
flowchart TB
    subgraph CLIENTS["Front ends"]
        direction LR
        subgraph DESK["🟦 Desktop (existing) + 🟩 Speedrun page"]
            SK["🟦 Svelte/SvelteKit pages<br/>ts/routes/*"]
            DASH["🟩 ts/routes/speedrun-dashboard/<br/>3-score UI (Memory live;<br/>Performance/Readiness stubbed)"]
            MANI["🟩 Manifold home screen (landing)<br/>qt/aqt/manifold.py · pgre.py<br/>Calabi-Yau + 9 PGRE points<br/>+ first-run default-deck import"]
            QT["🟦 PyQt shell + WebView<br/>qt/aqt/main.py · webview.py<br/>state 'manifold'"]
        end
        subgraph IOS["🟩 iOS app (Simulator + device .ipa)"]
            SWIFT["🟩 SwiftUI review + Scores + MCQ screens<br/>mobile/SpeedrunApp/<br/>AI grader: HeuristicCoach.swift"]
        end
    end

    subgraph TRANSPORT["Transport"]
        direction LR
        HTTP["🟦 HTTP POST /_anki/{method}<br/>ts/lib/generated/post.ts :: postProto()<br/>→ qt/aqt/mediasrv.py :: handle_request()"]
        PYO3["🟦 PyO3 FFI<br/>pylib/rsbridge/lib.rs :: command()"]
        CFFI["🟩 C-ABI FFI (new staticlib)<br/>mobile/anki-ffi/ :: anki_command()<br/>→ .xcframework (aarch64-apple-ios-sim<br/>+ aarch64-apple-ios device slice → unsigned .ipa)"]
    end

    PYLIB["🟦 Python library<br/>pylib/anki/collection.py · _backend.py<br/>🟩 pylib/anki/speedrun.py (wrapper)"]

    subgraph CORE["🟦 Rust core — rslib/"]
        DISPATCH["🟦 RPC dispatcher (numeric service/method)<br/>rslib/rust_interface.rs :: run_service_method()<br/>backend/mod.rs :: with_col()"]
        SCHED["🟦 SchedulerService + FSRS<br/>scheduler/queue · answering · fsrs/"]
        SEARCH["🟦 Search: string→AST→SQL<br/>search/parser · sqlwriter · builder"]
        SPEED["🟩 SpeedrunService.TopicMastery (NEW)<br/>rslib/src/speedrun/{mod,service}.rs<br/>read-only · reuses search + FSRS + revlog"]
        STORE["🟦 SQLite storage<br/>rslib/src/storage/"]
    end

    DB[("⬜ collection.anki2<br/>cards · notes · revlog<br/>(taken_millis = latency)")]
    PROTO["🟨 proto/anki/*.proto<br/>🟩 + speedrun.proto<br/>drives codegen for ALL layers"]

    SK --> HTTP
    DASH --> HTTP
    MANI --> QT
    QT --> PYLIB
    SWIFT --> CFFI

    HTTP --> DISPATCH
    PYLIB --> PYO3 --> DISPATCH
    CFFI --> DISPATCH

    DISPATCH --> SCHED
    DISPATCH --> SEARCH
    DISPATCH --> SPEED
    SPEED -.->|"composes"| SEARCH
    SCHED --> STORE
    SEARCH --> STORE
    SPEED --> STORE
    STORE --> DB

    PROTO -.->|codegen| DISPATCH
    PROTO -.->|codegen| HTTP
    PROTO -.->|codegen| PYLIB
    PROTO -.->|"swift-protobuf"| SWIFT

    classDef existing fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef new fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef gen fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef store fill:#e5e7eb,stroke:#6b7280,color:#111827;

    class SK,QT,HTTP,PYO3,PYLIB,DISPATCH,SCHED,SEARCH,STORE existing;
    class DASH,MANI,SWIFT,CFFI,SPEED new;
    class PROTO gen;
    class DB store;
```

**Reading it:** both apps speak the _same_ protobuf to the _same_ Rust engine —
desktop through PyO3/HTTP, iOS through a new tiny C-ABI. The only engine change is
one **read-only** RPC (`TopicMastery`) that composes existing search + FSRS +
revlog primitives, so undo and DB integrity are untouched (the spec's key claim).

**Desktop landing screen:** the fork opens on a **Calabi-Yau manifold home
screen** ([qt/aqt/manifold.py](qt/aqt/manifold.py), HTML from
[qt/aqt/pgre.py](qt/aqt/pgre.py) `build_manifold_html`) instead of the deck list
— a new `"manifold"` `MainWindowState` in [qt/aqt/main.py](qt/aqt/main.py). Its
9 outer points open the PGRE decks' Study Now overview; a "Classic deck list"
link falls back to the intact `DeckBrowser`. On a fresh collection, first launch
auto-imports the 9 bundled `categorized decks/` `.apkg` files into
`PGRE::<Subject>` decks (`_seed_default_decks` → `import_default_decks`, guarded
by `pgreDefaultDecksImported`).

---

## 2. The one real Rust change — `TopicMastery` end-to-end

```mermaid
flowchart LR
    subgraph IN["Callers (same RPC, 3 hosts)"]
        TS["🟩 dashboard<br/>@generated/backend"]
        PY["🟩 col.speedrun / _backend.topic_mastery()"]
        SW["🟩 (iOS, later) anki_command()"]
    end

    TS --> POST["🟦 postProto → mediasrv"]
    PY --> RB["🟦 rsbridge.command()"]
    SW --> FF["🟩 anki_command()"]
    POST --> DISP
    RB --> DISP
    FF --> DISP

    DISP["🟦 run_service_method(service,method,bytes)<br/>with_col() acquires collection"]
    DISP --> IMPL["🟩 speedrun/service.rs :: topic_mastery()"]

    subgraph LOGIC["🟩 speedrun/mod.rs — single scan, O(C+R)"]
        Q1["1. scan cards⋈notes<br/>map tag pgre::&lt;subject&gt; → [SubjectAccum; 9]"]
        Q2["2. per card R =<br/>current_retrievability_seconds(state, secs, decay)<br/>(FSRS::new hoisted out of loop)"]
        Q3["3. scan revlog⋈cards<br/>median taken_millis via select_nth_unstable"]
        Q4["4. coverage = Σ weight(subject ≥1 card)<br/>memory_score = coverage-weighted mean R<br/>Wilson range · confidence · reasons"]
        Q5{"give-up rule?<br/>reviews&lt;100 ∨ coverage&lt;40%<br/>∨ a ≥10% subject has 0 cards"}
    end

    IMPL --> Q1 --> Q2 --> Q3 --> Q4 --> Q5
    Q5 -->|yes| AB["abstain = true<br/>(no bare number)"]
    Q5 -->|no| SC["ScoreCard{estimate, low, high,<br/>coverage, confidence, updated_at, reasons[]}"]

    REUSE["🟦 reused primitives:<br/>search_cards · Card.memory_state<br/>FsrsMemoryState · revlog.taken_millis<br/>browser_table retrievability pattern"]
    REUSE -.-> LOGIC

    classDef existing fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    classDef new fill:#dcfce7,stroke:#16a34a,color:#14532d;
    class POST,RB,DISP,REUSE existing;
    class TS,PY,SW,FF,IMPL,Q1,Q2,Q3,Q4,Q5,AB,SC new;
```

---

## 3. The three scores & the honesty rule (product core)

```mermaid
flowchart TD
    REV["🟦 Reviews on shared engine<br/>(desktop + iOS) → revlog<br/>FSRS memory_state + taken_millis"]

    REV --> MEM["🟩 MEMORY<br/>recall of a taught fact<br/>FSRS-derived · LIVE"]
    REV -.-> PERF["🟩 PERFORMANCE<br/>P(correct on NEW exam-style Q)<br/>LIVE · MCQ practice graded by<br/>AI Heuristic Coach<br/>(qt/aqt/heuristic_coach.py ·<br/>HeuristicCoach.swift)"]
    REV -.-> READY["🟩 READINESS<br/>projected 200–990 + range · LIVE"]

    MEM --> HON{{"Honesty rule —<br/>show all 7 or ABSTAIN:<br/>estimate · range · coverage ·<br/>confidence · updated_at · reasons · give-up rule"}}
    HON -->|enough data| SHOW["🟩 Dashboard renders score card"]
    HON -->|insufficient| ABS["🟩 'Not enough data yet —<br/>here's what's missing'"]

    NOTE["⚠ Why 3 separate scores:<br/>Brainlift — daily Anki + 12-wk plan<br/>still plateaued ~800.<br/>Memory ≠ Performance ≠ Readiness."]
    NOTE -.-> MEM

    classDef new fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef note fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef existing fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;
    class MEM,PERF,READY,SHOW,ABS new;
    class REV existing;
    class NOTE note;
```

---

## 4. Wednesday MVP build plan (SPECS S0–S9 dependency graph)

```mermaid
flowchart LR
    S0["🟩 S0 build bring-up<br/>just run / just check green"]
    S0p["🟩 S0' iOS toolchain<br/>Xcode + ios-sim target"]
    S1["🟩 S1 deck prep<br/>tag pgre::&lt;subject&gt; → .colpkg<br/>(speedrun/*.py)"]

    S2["🟩 S2 Rust RPC<br/>TopicMastery"]
    S3["🟩 S3 score math<br/>+ honesty"]
    S4["🟩 S4 Python wrapper"]
    S5["🟩 S5 Svelte dashboard"]
    S6["🟩 S6 iOS C-FFI<br/>xcframework"]
    S7["🟩 S7 SwiftUI review"]
    S8["🟩 S8 latency surfacing"]
    S9["🟩 S9 installer + proof"]

    S0 --> S2
    S0 --> S5
    S0 --> S6
    S0p --> S6
    S1 --> S5
    S1 --> S7
    S2 --> S3
    S2 --> S4 --> S5
    S2 --> S8 --> S5
    S6 --> S7
    S5 --> S9
    S7 --> S9

    PAR["▷ Parallel tracks:<br/>S1 from hour 0 · S2/S3 (Rust) ∥ S6 (iOS)<br/>⚠ serialize: proto edits + lib.rs registration"]
    PAR -.-> S2

    classDef new fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef note fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    class S0,S0p,S1,S2,S3,S4,S5,S6,S7,S8,S9 new;
    class PAR note;
```

---

## 5. How later deadlines slot in (additive, no rework)

```mermaid
flowchart LR
    subgraph WED["Wednesday MVP"]
        W["🟩 2 apps · 1 engine · 1 RPC<br/>Memory score (honest) · review loop<br/>desktop installer · iOS sim"]
    end
    subgraph FRI["Friday"]
        F["🟩 AI service + Claude adapter (flag-gated)<br/>two-way sync (reuse SyncService)<br/>fill Performance + Readiness cards"]
    end
    subgraph SUN["Sunday"]
        SU["🟩 calibration (Brier/log-loss)<br/>score→200–990 mapping<br/>SPEED-MODE ABLATION (on/off/plain)<br/>signed installers · TestFlight"]
    end

    W -->|"latency logged from day 1<br/>ScoreCard shape reused<br/>AI/sync seams reserved"| F --> SU

    classDef new fill:#dcfce7,stroke:#16a34a,color:#14532d;
    class W,F,SU new;
```

---

## Quick map: doc → what it answers

| Question                                   | Doc                                                                                                                                          |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Where is feature X's file+function?        | [CODE_MAP.md](CODE_MAP.md)                                                                                                                   |
| What is each technology / crate?           | [docs/tech-stack.md](docs/tech-stack.md)                                                                                                     |
| What happens to one RPC at runtime?        | [docs/data-flow.md](docs/data-flow.md)                                                                                                       |
| How is `rslib` organized?                  | [docs/rust-core.md](docs/rust-core.md)                                                                                                       |
| Desktop UI: manifold home + default decks? | [CODE_MAP.md](CODE_MAP.md) (Diagram 6), [docs/data-flow.md](docs/data-flow.md), [categorized decks/README.md](categorized%20decks/README.md) |
| Why these product choices?                 | [PRD.md](PRD.md)                                                                                                                             |
| What exactly to build + test thresholds?   | [SPECS.md](SPECS.md)                                                                                                                         |
| Deck-prep / fixture tooling?               | [speedrun/README.md](speedrun/README.md)                                                                                                     |
