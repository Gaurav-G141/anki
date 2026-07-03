# Speedrun (Physics GRE) — an Anki fork

> **Exam: the Physics GRE (PGRE)** — a single scaled score from 200–990 in
> 10-point increments (no official subscores). This fork breaks memory/mastery
> down by the nine ETS content areas (Classical Mechanics, Electromagnetism,
> Quantum Mechanics, Atomic Physics, Thermodynamics & Statistical Mechanics,
> Optics & Waves, Specialized Topics, Special Relativity, Laboratory Methods)
> for targeted study.
>
> This is a **fork of [Anki](https://apps.ankiweb.net)** adding a desktop + iOS
> study app that shares one Rust engine, with an honest per-topic _memory score_.
> It stays licensed **AGPL-3.0-or-later** and credits the upstream Anki project
> and its contributors. New work lives in `speedrun/`, `rslib/src/speedrun/`,
> `proto/anki/speedrun.proto`, `ts/routes/speedrun-dashboard/`, and `mobile/`.
> See [PRD.md](./PRD.md), [SPECS.md](./SPECS.md),
> [speedrun/RUST_CHANGE.md](./speedrun/RUST_CHANGE.md), and
> [speedrun/MANUAL_TEST.md](./speedrun/MANUAL_TEST.md).
>
> **Building the apps yourself:** see
> [BUILD_INSTALLERS.md](./BUILD_INSTALLERS.md) for step-by-step instructions to
> build the macOS `.dmg` installer and the iOS Simulator app from source
> (including how to run the iOS app in the emulator).
>
> **See the full app with realistic progress:** [dummy_account.md](./dummy_account.md)
> loads a pre-seeded "moderate progress" learner so all three scores (Memory /
> Performance / Readiness) render at once — no grinding reviews first.

---

# Anki

[![Build Status](https://github.com/ankitects/anki/actions/workflows/ci.yml/badge.svg)](https://github.com/ankitects/anki/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-dev--docs.ankiweb.net-blue)](https://dev-docs.ankiweb.net)

This repo contains the source code for the computer version of
[Anki](https://apps.ankiweb.net).

## About

Anki is a spaced repetition program. Please see the [website](https://apps.ankiweb.net) to learn more.

## Getting Started

### Contributing

Want to contribute to Anki? Check out the [Contribution Guidelines](./docs/contributing.md).

For more information on building and developing, please see [Development](./docs/development.md).

#### Contributors

The following people have contributed to Anki: [CONTRIBUTORS](./CONTRIBUTORS)

### Anki Betas

If you'd like to try development builds of Anki but don't feel comfortable
building the code, please see [Anki betas](https://betas.ankiweb.net/).

## License

Anki's license: [LICENSE](./LICENSE)
