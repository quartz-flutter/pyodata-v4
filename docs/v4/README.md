# OData v4 compatibility project

This directory is the working record of the effort to add OData v4 support to
this v2 client **without degrading the v2 implementation**.

Everything here is research and planning. No `pyodata/v4/` code exists yet —
[phase 0](plan/roadmap.md#phase-0--safety-net) is complete, so what exists is
the safety net that makes the later phases checkable.

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
- [`../../tests/fixtures/v4/`](../../tests/fixtures/v4/PROVENANCE.md) — the
  vendored normative material: the OASIS ABNF grammar and its 840-vector test
  corpus, and the three annotation vocabularies (Core, Capabilities, SAP
  Common) carrying the terms phase 3 maps onto the v2 `sap:*` surface. Pinned
  by commit, never fetched at test time. The other four vocabularies named in
  `research/resources.md` are deliberately absent — PROVENANCE.md records why,
  and a test keeps them out.

## Status

| | |
|---|---|
| Phase | 0 complete — the safety net is in place; phase 1 is next |
| v2 baseline | 393 tests passing, 93% line coverage, Python 3.11 / lxml 6.x (`make test`) |
| v4 code | none yet, by design — phase 0 adds no `pyodata/` source changes |
| Gates live | G1 API snapshot, G2 wire-format golden tests, coverage floors in CI |
| Normative specs | obtained and vendored, see [research/resources.md](research/resources.md) and [the provenance record](../../tests/fixtures/v4/PROVENANCE.md) |
| Branches | feature branches off `master`, per CLAUDE.md; phase 0 landed on `claude/phase-0-setup-jgigth` |
| Last updated | 2026-08-30 |

### What phase 0 delivered

| Roadmap item | Where it lives |
|---|---|
| 1. Toolchain fixed (`make lint` runs on Python ≥3.11) | `dev-requirements.txt`, `.pylintrc` |
| 2. G1 public API snapshot | `tests/test_public_api_snapshot.py`, `tests/public_api_snapshot.json` |
| 3. G2 v2 wire-format golden tests | `tests/test_wire_format_golden_v2.py` |
| 4. Coverage baseline enforced in CI | `tests/check_coverage_floors.py`, `make coverage-floors` |
| 5. ABNF corpus + vocabularies vendored | `tests/fixtures/v4/`, `tests/test_v4_reference_corpus.py` |

Two findings from phase 0 that phase 4 should not rediscover: the ABNF corpus
cannot be read with `yaml.safe_load` (a deliberate raw tab, and YAML implicit
resolvers that corrupt OData date literals — use
`tests.conftest.load_abnf_testcases()`), and the corpus lists this client's
current `X'…'` binary literal form as a **negative** vector, which is rule R5
made concrete.
