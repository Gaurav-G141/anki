# Tech Stack

A tour of the technologies Anki is built from, written for coding agents and new
contributors. Anki's stack is unusually wide, and several pieces are uncommon
enough that you may not recognize them on sight. This document catalogs the whole
stack but **leads with the surprising parts** — read those first.

For _how the layers fit together_ see [architecture.md](./architecture.md),
[data-flow.md](./data-flow.md), and [rust-core.md](./rust-core.md); this doc is
about _what each thing is_.

## Orientation

Anki is five cooperating layers, each with its own language:

| Layer              | Language                | Where                                 |
| ------------------ | ----------------------- | ------------------------------------- |
| Core engine        | **Rust**                | [rslib/](../rslib/)                   |
| Python↔Rust bridge | Rust (PyO3)             | [pylib/rsbridge/](../pylib/rsbridge/) |
| Library API        | **Python**              | [pylib/anki/](../pylib/anki/)         |
| Desktop GUI        | **Python + PyQt6**      | [qt/aqt/](../qt/aqt/)                 |
| Web frontend       | **TypeScript + Svelte** | [ts/](../ts/)                         |

The layers talk to each other through **Protocol Buffers**, and the whole thing
is assembled by a **custom, Rust-authored build system**. Those two facts plus
the i18n system are the keys to the codebase, so they lead the next section.

## Things you probably haven't seen before

Each entry: _what it is → where it's used → the gotcha._

### Project Fluent (`.ftl`) for translations

**What:** [Project Fluent](https://projectfluent.org/) is Mozilla's localization
system. Instead of gettext `.po` files, translations live in `.ftl` files with a
declarative syntax that handles plurals and variants natively.

**Where:** source strings live in [ftl/core/](../ftl/) (and `ftl/qt/`); the
machinery is in [rslib/i18n/](../rslib/i18n/). Runtime is the `fluent` crate
(0.17) in Rust and `@fluent/bundle` (^0.19) in TypeScript.

**Gotcha:** the per-language translation APIs are **code-generated** from the
`.ftl` files. You edit the `.ftl` files (in `ftl/core` or `ftl/qt`) and _use_ the
generated, type-safe accessors — you never edit the generated functions. See the
translations note in the project `CLAUDE.md`/`AGENTS.md`.

### Protocol Buffers as the cross-language API

**What:** the `.proto` files in [proto/anki/](../proto/) define every backend
method and several on-disk storage formats. They are the contract between Rust,
Python, and TypeScript.

**Where:** compiled by `prost` (0.13) for Rust and by `protoc-gen-es` /
`@bufbuild/protobuf` (^1.x) for TypeScript; `protoc` itself (v31.1) is downloaded
at build time. The generated services drive a numeric RPC dispatch.

**Gotcha:** RPCs are addressed by `(service_index, method_index)` integers, not
names, and clients just send `(service, method, bytes)`. Full mechanics in
[data-flow.md](./data-flow.md); conventions in [protobuf.md](./protobuf.md). The
protobuf is **not** a public API.

### PyO3 / `rsbridge` — Rust compiled into Python

**What:** [PyO3](https://pyo3.rs) (0.29) lets the Rust core be compiled as a
native Python extension module (`_rsbridge`).

**Where:** [pylib/rsbridge/](../pylib/rsbridge/). This is the **single FFI
boundary** between Python and Rust — everything else flows through it as protobuf
bytes (see [data-flow.md](./data-flow.md)).

**Gotcha:** it's built against the `abi3` stable ABI (`abi3-py39`), so one wheel
works across Python 3.9+. Linking is fussy on macOS/Windows; see
[.cargo/config.toml](../.cargo/config.toml).

### A custom, Rust-authored build system

**What:** there is no Makefile or plain Cargo workflow. The chain is
`just` → `ninja_gen` → `ninja`/`n2` → `runner`:

- [justfile](../justfile) — the recipes you actually run (`just run`, `just check`, …).
- [build/ninja_gen/](../build/ninja_gen/) — a Rust DSL that _generates_ a
  `build.ninja` manifest.
- `ninja` (or [n2](https://github.com/evmar/n2), a Rust reimplementation,
  auto-detected) executes that manifest.
- [build/runner/](../build/runner/) — runs individual build commands, downloads
  tools, etc.

External tools — `protoc` (31.1), `uv`, Node.js — are **downloaded and
SHA-verified at build time** by [build/ninja_gen/src/archives.rs](../build/ninja_gen/src/archives.rs).

**Gotcha:** per `CLAUDE.md`/`AGENTS.md`, **always use `just` recipes** — do not
invoke `./ninja`, `./run`, or scripts under `tools/` directly. Background in
[build.md](./build.md) and [ninja.md](./ninja.md).

### `uv` + Hatchling for Python

**What:** [`uv`](https://docs.astral.sh/uv/) (Astral) is the Python package and
workspace manager; Hatchling is the build backend. Not pip/poetry/setuptools.

**Where:** [pyproject.toml](../pyproject.toml) defines a uv workspace over
`pylib`, `qt`, and the installer plugins.

**Gotcha:** the build system pins and fetches `uv` itself; you don't manage the
venv by hand.

### Svelte 5 + the SvelteKit static adapter

**What:** the frontend is [Svelte](https://svelte.dev) 5 (the new _runes_
reactivity syntax) on [SvelteKit](https://kit.svelte.dev) 2, bundled by Vite 6.

**Where:** [ts/routes/](../ts/) for pages, [ts/lib/](../ts/lib/) for shared code.

**Gotcha:** it uses `@sveltejs/adapter-static` — the app builds to **static
files**, not a Node server. At runtime those files are served by an in-process
Flask/Waitress server ([qt/aqt/mediasrv.py](../qt/aqt/mediasrv.py)) and displayed
inside the Qt WebEngine (Chromium) view. There is **no Node.js at runtime**; Node
is a build-time dependency only.

### PyQt6 + QtWebEngine

**What:** the desktop shell is PyQt6 (≥6.2). `PyQt6-WebEngine` embeds Chromium,
which is what renders the Svelte frontend.

**Gotcha:** the Qt shell is deliberately thin — it hosts web views and bridges
JavaScript↔Python via `pycmd()`/`web.eval()` (see the "TypeScript from Python"
section of [language_bridge.md](./language_bridge.md)). UI layouts also come from
Qt Designer `.ui` XML files in [qt/aqt/forms/](../qt/aqt/forms/), compiled to
Python at build time.

### Notable Rust crates

- **[fsrs](https://github.com/open-spaced-repetition/fsrs-rs)** (5.2) — the FSRS
  spaced-repetition scheduling algorithm; core to Anki. Lives behind
  [rslib/src/scheduler/fsrs/](../rslib/src/scheduler/).
- **snafu** (0.8) — structured, context-rich error types. The convention inside
  `rslib` is `AnkiError`/`Result` + snafu; other crates use `anyhow` (see the
  error-handling note in `CLAUDE.md`/`AGENTS.md`).
- **camino** (1.1) — UTF-8 path types (`Utf8Path`) used instead of `std::path`
  so paths are guaranteed valid UTF-8.
- **nom** (8.0) — parser-combinator library behind the search-query parser
  ([rslib/src/search/](../rslib/src/search/)).
- **axum** (0.8) + **tokio** (1.45) — the async web framework and runtime powering
  the sync server/client ([rslib/src/sync/](../rslib/src/sync/)).
- **rusqlite** (0.36, bundled) — the SQLite binding for the collection database.

### Other languages and DSLs in the tree

You will also encounter: **Sass/SCSS** (styling, under `ts/lib/sass/` and
`sass/`), Qt Designer **`.ui` XML**, a small **Swift** macOS helper
([qt/mac/](../qt/mac/)), a **Ruby** Homebrew formula for building mpv
([qt/audio/mpv.rb](../qt/audio/mpv.rb)), and assorted **shell** scripts.

## Stack-by-layer reference

Versions reflect the manifests at time of writing; the manifests
([Cargo.toml](../Cargo.toml), [package.json](../package.json),
[pyproject.toml](../pyproject.toml)) are the source of truth.

### Rust core

| Tool / crate                        | Version                          | Purpose                                       |
| ----------------------------------- | -------------------------------- | --------------------------------------------- |
| Rust toolchain                      | 1.92.0 (edition 2021, MSRV 1.80) | [rust-toolchain.toml](../rust-toolchain.toml) |
| prost / prost-build / prost-reflect | 0.13 / 0.14                      | Protobuf codegen + reflection                 |
| rusqlite                            | 0.36 (bundled SQLite)            | Collection database                           |
| tokio / tokio-util                  | 1.45                             | Async runtime                                 |
| axum / axum-extra                   | 0.8                              | Sync server + endpoints                       |
| reqwest                             | 0.12                             | HTTP client (sync)                            |
| serde / serde_json                  | 1.0                              | Serialization                                 |
| snafu / anyhow                      | 0.8 / 1.0                        | Error handling                                |
| nom                                 | 8.0                              | Search-query parser                           |
| fsrs                                | 5.2                              | Spaced-repetition algorithm                   |
| fluent / fluent-bundle              | 0.17 / 0.16                      | i18n runtime                                  |
| camino                              | 1.1                              | UTF-8 paths                                   |
| pyo3                                | 0.29 (abi3-py39)                 | Python FFI (in `rsbridge`)                    |

### Frontend (TypeScript / Svelte)

| Tool / package                     | Version     | Purpose                             |
| ---------------------------------- | ----------- | ----------------------------------- |
| svelte                             | ^5.55       | UI framework (runes)                |
| @sveltejs/kit                      | ^2.60       | App framework                       |
| @sveltejs/adapter-static           | ^3.0        | Static-site build (no Node runtime) |
| vite                               | 6           | Bundler / dev server                |
| typescript                         | ^5.0        | Language                            |
| @bufbuild/protobuf / protoc-gen-es | ^1.2 / ^1.8 | Protobuf runtime + codegen          |
| @fluent/bundle                     | ^0.19       | i18n runtime                        |
| d3                                 | ^7          | Graphs                              |
| fabric                             | ^5.3        | Image-occlusion canvas              |
| codemirror                         | ^5.63       | Code/HTML editing                   |
| mathjax                            | ^3.1        | Math rendering                      |
| Yarn                               | 4.11.0      | Package manager                     |
| Vitest / Playwright                | ^3 / ^1.60  | Unit / e2e tests                    |

### Python / Qt

| Tool / package          | Version                        | Purpose                         |
| ----------------------- | ------------------------------ | ------------------------------- |
| Python                  | ≥3.12 (root), ≥3.10 (pylib/qt) | Runtime                         |
| PyQt6 / PyQt6-WebEngine | ≥6.2                           | Desktop GUI + embedded Chromium |
| protobuf                | ≥6.0,<8.0                      | Protobuf runtime                |
| Flask / Waitress        | — / ≥2.0                       | In-process media/page server    |
| orjson                  | —                              | Fast JSON                       |
| uv                      | (build-managed)                | Package/workspace manager       |
| Hatchling               | —                              | Build backend                   |
| ruff / mypy / pytest    | (build-managed)                | Lint / typecheck / test         |

### Build, codegen, and docs

| Tool                           | Version           | Purpose                                             |
| ------------------------------ | ----------------- | --------------------------------------------------- |
| just                           | —                 | Task runner ([justfile](../justfile))               |
| ninja_gen + ninja/n2           | —                 | Generates and runs `build.ninja`                    |
| protoc                         | 31.1 (downloaded) | Protobuf compiler                                   |
| Sphinx + MyST + sphinx-autoapi | —                 | These dev docs (ReadTheDocs)                        |
| Mintlify                       | (hosted)          | User-facing docs site ([docs-site/](../docs-site/)) |

## Where generated code lives

A lot of code does not exist until you build. After a build, look under `out/`
and `$OUT_DIR`:

- `$OUT_DIR/backend.rs` — generated Rust service traits + RPC dispatcher.
- `out/pylib/anki/_backend_generated.py` and `out/pylib/anki/*_pb2.py` — generated
  Python backend methods and protobuf messages.
- `out/ts/lib/generated/` — the `@generated/backend` and `@generated/ftl` modules.

See [rust-core.md](./rust-core.md) and [data-flow.md](./data-flow.md) for how
these are wired together.
