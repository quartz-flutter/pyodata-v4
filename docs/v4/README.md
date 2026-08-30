# OData v4 compatibility project

This directory is the working record of the effort to add OData v4 support to
this v2 client **without degrading the v2 implementation**.

Everything here is research and planning. No `pyodata/v4/` code exists yet.

## Read in this order

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [research/parser-behaviour-v4-input.md](research/parser-behaviour-v4-input.md) | What *actually* happens today when you feed v4 metadata to this library. Measured, not assumed. |
| 2 | [research/protocol-delta.md](research/protocol-delta.md) | Every v2 -> v4 difference that this client's surface touches. |
| 3 | [research/codebase-audit.md](research/codebase-audit.md) | Where the v2 assumptions physically live, by file and line. |
| 4 | [research/prior-art.md](research/prior-art.md) | What upstream and the wider Python ecosystem already tried, and why we are not copying it. |
| 5 | [plan/architecture.md](plan/architecture.md) | The chosen design and the alternatives rejected. |
| 6 | [plan/compatibility-contract.md](plan/compatibility-contract.md) | The rules that make "no deterioration" enforceable rather than aspirational. |
| 7 | [plan/roadmap.md](plan/roadmap.md) | Phases, deliverables, exit criteria. |
| 8 | [plan/conformance-matrix.md](plan/conformance-matrix.md) | Feature-by-feature status tracker. |
| — | [research/resources.md](research/resources.md) | Specification and reference bibliography. |

## Fixtures

- [`fixtures/trippin-v4-metadata.xml`](fixtures/trippin-v4-metadata.xml) — a
  hand-written CSDL 4.0 document modelled on the OData TripPin reference service.
  It deliberately exercises the constructs that have no v2 equivalent:
  `NavigationProperty` with `Partner`/`ContainsTarget`, `NavigationPropertyBinding`,
  `Singleton`, `TypeDefinition`, schema-level `Function`/`Action`, `BaseType`
  inheritance, inline `Annotation`, and the `Edm.Date` / `Edm.TimeOfDay` /
  `Edm.Duration` primitives. Used to produce the measurements in document 1.

## Status

| | |
|---|---|
| Phase | 0 — research and planning (this directory) |
| v2 baseline | 263 tests passing, 91% line coverage, Python 3.11 / lxml 6.x |
| v4 code | none yet |
| Normative specs | obtained — OASIS sources are on GitHub, see [research/resources.md](research/resources.md) |
| Branch | `claude/odata-v4-compatibility-50ejxo` |
| Last updated | 2026-08-30 |
