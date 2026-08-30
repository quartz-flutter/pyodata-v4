# Vendored OData v4 reference material

Phase 0 item 5 of [`../../../docs/v4/plan/roadmap.md`](../../../docs/v4/plan/roadmap.md).

These files are **pinned copies of third-party normative material**, vendored so
the test suite never reaches the network. Nothing here is fetched at test time,
and nothing here is ours.

## Rules for this directory

1. **Never edit these files.** They are upstream artefacts, byte-exact. A local
   quirk is worked around in the loader (`tests/conftest.py`), never by
   "fixing" the data — a corpus you have edited no longer proves anything.
2. **Re-pin, don't patch.** To take a newer upstream version, re-copy from the
   named commit and update the table below, including the checksums, in the
   same commit.
3. **These files are not Apache-2.0.** The OASIS material is governed by the
   OASIS IPR Policy, not by this repository's licence; see
   [`../../../.reuse/dep5`](../../../.reuse/dep5), which records this.

## What is here, and from where

Vendored 2026-08-30.

### `abnf/` — from [`oasis-tcs/odata-abnf`](https://github.com/oasis-tcs/odata-abnf)

Commit `a31c8db229a0d8e957bee86512b01efe7ce74173` (`main`, 2026-08-26).
Licence: OASIS IPR Policy, RF on RAND Mode.

| File | Lines | SHA-256 |
|---|---|---|
| `odata-abnf-construction-rules.txt` | 1298 | `35e515ebe62a273f2fe28da289bf9426a933338b958b6b75bc7030810d44ab5c` |
| `odata-abnf-testcases.yaml` | 3770 | `feded192570e4c7e64c60b47d9631ae20da7cd1c974d54ae58111cd84d12c921` |

The construction rules are the complete OData 4.01/4.0 URL and literal grammar.
The test cases are a machine-readable corpus keyed by grammar rule: **840
vectors across 83 rules, of which 79 are negative**, annotated with `FailAt`,
the character offset at which parsing must fail.

Read it with `tests.conftest.load_abnf_testcases()`. Do not call
`yaml.safe_load` on it directly — see the two upstream quirks below.

The same commit also carries `odata-aggregation-abnf.txt` /
`odata-aggregation-testcases.yaml` (the `$apply` grammar) and the temporal
pair. They are deliberately not vendored yet; phase 5 should re-pin from this
same commit if it wants them.

#### Two quirks that will bite anyone loading this file naively

Both are properties of the corpus, not defects, and both are handled by
`load_abnf_testcases()`:

* **One raw tab.** Line 2551 is `Input: $orderby=Name<TAB>asc` — the vector
  proving a tab is a valid separator in `$orderby`. PyYAML's scanner refuses a
  tab in that position and raises `found character '\t' that cannot start any
  token`.
* **YAML implicit resolvers corrupt OData literals.** The corpus contains
  `0000-01-01`, a legal `Edm.Date` value that is not a representable Python
  date; `yaml.safe_load` raises `ValueError: year 0 is out of range` on it.
  Scalars such as `true` and `42` would likewise arrive as a bool and an int
  rather than as the text the grammar is about.

#### Vectors worth knowing about before phase 4

* `binaryLiteral` has 10 vectors, including `X'1a2B3c4D'` as a **negative**
  case (`FailAt: 0`). That is the v2 form this client emits today
  (`EdmBinaryTypTraits('(?:binary|X)')`), and v4 must reject it — a concrete
  instance of why the v4 traits need their own registry (contract rule R5).
* `odataUri` has 24 vectors; validating whole generated URLs against that rule
  needs an ABNF engine, which the roadmap permits as a **test-only**
  dependency. The per-type literal rules need no such engine and are the
  cheaper win.

### `vocabularies/` — CSDL 4.0 annotation vocabularies

Three vocabularies, not the seven listed in
[`../../../docs/v4/research/resources.md`](../../../docs/v4/research/resources.md).
These are the ones that carry terms phase 3 item 8 actually has to map, so
that v4 metadata presents the same `label` / `creatable` / `updatable` /
`sortable` / `filterable` / `text` surface that v2 builds from `sap:*`
attributes:

| Need, as v2 expresses it | v4 term |
|---|---|
| `sap:label`, `sap:text` | `Common.Label`, `Common.Text` |
| SAP value help (`SAP_ANNOTATION_VALUE_LIST`) | `Common.ValueList` |
| `sap:creatable`, `sap:updatable` | `Capabilities.InsertRestrictions`, `Capabilities.UpdateRestrictions` |
| `sap:filterable`, `sap:sortable` | `Capabilities.FilterRestrictions`, `Capabilities.SortRestrictions` |
| — (v4 additions the above build on) | `Core.Description`, `Core.Computed`, `Core.Immutable` |

They are here to pin the exact term names, record shapes and property names, so
the mapping is read off the normative definition rather than guessed. Getting a
record property name wrong is a silent mis-mapping, not a crash.

From [`oasis-tcs/odata-vocabularies`](https://github.com/oasis-tcs/odata-vocabularies),
commit `b4597c0a21adc57a80c98046a616eb84f86149a8` (`main`, 2026-08-26).
Licence: OASIS IPR Policy, RF on RAND Mode.

| File | Namespace | SHA-256 |
|---|---|---|
| `Org.OData.Core.V1.xml` | `Org.OData.Core.V1` | `cb39e966748a7ef5d831cd5f886f4f3ddf1cfa8a4f6b0186c832028c5502482c` |
| `Org.OData.Capabilities.V1.xml` | `Org.OData.Capabilities.V1` | `fd4d9e5cc4daba2afc76239765716e81f4ed0ec76d8548037b853b009864f339` |

From [`SAP/odata-vocabularies`](https://github.com/SAP/odata-vocabularies),
commit `db776bc686e186e32536e527e7a6e51000beaf47` (`main`, 2026-08-27).
Licence: Apache-2.0.

| File | Upstream name | Namespace | SHA-256 |
|---|---|---|---|
| `com.sap.vocabularies.Common.v1.xml` | `vocabularies/Common.xml` | `com.sap.vocabularies.Common.v1` | `1a58bd3424eca21a0c535a6db9ec5e825b9890de3bef63de8d6fde8b0aedc414` |

The SAP file is renamed to its declared schema namespace so all three are
addressable the same way; its contents are unmodified.

### Deliberately not vendored

Vendored data is not free — it is reviewed, licensed and carried forever — so
a file earns its place by having a named consumer, not by being related to the
subject. These were vendored in the first pass and then removed for failing
that test:

| Not here | Why not | If you need it |
|---|---|---|
| `com.sap.vocabularies.UI.v1.xml` | 2,067 lines of Fiori **screen layout** terms — `LineItem`, `FieldGroup`, `DataPoint`, `KPI`, `GeoPoints`. This is an HTTP client library; it renders nothing. No consumer, now or in any planned phase. | SAP commit `db776bc`, `vocabularies/UI.xml` |
| `Org.OData.Aggregation.V1.xml` | Only used by `$apply`, which is phase 5 — the phase the roadmap itself calls severable. Speculative until that ships. | OASIS commit `b4597c0` |
| `Org.OData.Measures.V1.xml` | Unit/currency annotations. v2 exposes no unit concept, so there is nothing to map them onto. | OASIS commit `b4597c0` |
| `Org.OData.Validation.V1.xml` | No consumer in the planned v4 surface. | OASIS commit `b4597c0` |

Re-adding any of them is a copy from the commit named above plus a row in the
table here and an entry in `VOCABULARIES` in
`tests/test_v4_reference_corpus.py`. Do that when a phase has a concrete use
for the terms, not before.

The same applies to `odata-aggregation-abnf.txt` /
`odata-aggregation-testcases.yaml` and the temporal pair, which live at ABNF
commit `a31c8db` alongside the two files that are vendored here.
