# Resource bibliography

## OData v4 — normative specifications (OASIS)

The 4.01 versions are current; 4.0 is what most deployed services (including SAP
S/4HANA) actually emit. Implement against 4.0 and accept 4.01 extensions.

| Document | URI |
|---|---|
| OData Version 4.01 Part 1: Protocol | `https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part1-protocol.html` |
| OData Version 4.01 Part 2: URL Conventions | `https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html` |
| OData CSDL **XML** Representation 4.01 | `https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/odata-csdl-xml-v4.01.html` |
| OData CSDL **JSON** Representation 4.01 | `https://docs.oasis-open.org/odata/odata-csdl-json/v4.01/odata-csdl-json-v4.01.html` |
| OData **JSON Format** 4.01 | `https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html` |
| OData Extension for Data Aggregation (`$apply`) 4.0 | `https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.html` |
| OData 4.0 (errata 03) Part 1–3 — note 4.0 had a "Part 3: CSDL"; in 4.01 CSDL became the two standalone documents above | `https://docs.oasis-open.org/odata/odata/v4.0/odata-v4.0-part1-protocol.html` |
| ABNF grammars (`odata-abnf-construction-rules.txt`) | `https://docs.oasis-open.org/odata/odata/v4.01/csprd06/abnf/` |

> **`docs.oasis-open.org` and `www.odata.org` are blocked by this sandbox's
> egress proxy — but the normative sources are on GitHub, which is reachable.**
> Use the repositories in the next section instead of the URIs above. The URIs
> remain the citable addresses for the published documents.

## Normative sources as git repositories (the practical route)

Verified reachable and cloned on 2026-08-30.

| Repository | Contents |
|---|---|
| `https://github.com/oasis-tcs/odata-specs` | **The specs themselves**, as authored markdown. Directories: `odata-csdl/`, `odata-json-format/`, `odata-url-conventions/`, `odata-protocol/`, `odata-data-aggregation-ext/`, `odata-temporal-ext/`. ~1.4 MB of normative text. |
| `https://github.com/oasis-tcs/odata-abnf` | **`abnf/odata-abnf-construction-rules.txt`** (1298 lines, the complete URL and literal grammar) and **`abnf/odata-abnf-testcases.yaml`** (3770 lines of positive *and negative* test vectors for 4.01 and 4.0). |
| `https://github.com/oasis-tcs/odata-vocabularies` | OASIS vocabulary definitions (Core, Capabilities, Measures, Validation, Aggregation) as CSDL. |
| `https://github.com/SAP/odata-vocabularies` | SAP vocabularies (`com.sap.vocabularies.*`) as CSDL. |

### Two cautions when using `odata-specs`

1. **`main` is the 4.02 working draft**, not a published standard — its
   frontmatter templates resolve to `.../v4.02/...`. Target 4.0/4.01 behaviour
   and treat anything that appears only on `main` as provisional. Published
   stages are tagged (`git ls-remote --tags origin`); the aggregation extension
   has proper `V4.0_CS03`/`CS04` tags, the core bundle currently only carries
   `core/V4.02_CSD01`/`CSD02`.
2. The markdown carries templating placeholders (`$$$pagetitle$$$`) and
   cross-reference macros. It is normative prose, not a rendered document.

### `odata-abnf-testcases.yaml` is the highest-value artefact here

It is a machine-readable corpus keyed by grammar rule — `entitySetName`,
`entityFunctionImport`, `complexColProperty`, `actionImport`, and ~100 more —
with positive cases and negative cases annotated by the character offset at
which parsing should fail. It maps directly onto a pytest-parametrized test
suite for the v4 literal and URL layer, which is exactly the area where a
hand-written client accumulates silent bugs. **Vendor a pinned copy into
`tests/fixtures/v4/` rather than fetching it at test time.**

### Spot-checks already performed against these sources

| Claim in [protocol-delta.md](protocol-delta.md) | Confirmed by |
|---|---|
| `contains(field, value)` — argument order reversed vs v2 `substringof` | `odata-url-conventions/5 Query Options.md:606,627` — `contains(CompanyName,'Alfreds')` |
| `ContainsTarget` is a navigation-property facet | `odata-csdl/7 Structural Property.md:553-560` |

## OData v2 — for the frozen side of the contract

| Document | URI |
|---|---|
| OData Version 2.0 overview | `https://www.odata.org/documentation/odata-version-2-0/overview/` |
| OData 2.0 JSON (verbose) format | `https://www.odata.org/documentation/odata-version-2-0/json-format/` |
| OData 2.0 URI conventions | `https://www.odata.org/documentation/odata-version-2-0/uri-conventions/` |
| OData 2.0 batch processing | `https://www.odata.org/documentation/odata-version-2-0/batch-processing/` (already cited in `pyodata/v2/service.py`) |

## Vocabularies (annotation terms, needed to replace `sap:*` attributes)

| Vocabulary | Namespace |
|---|---|
| Core | `Org.OData.Core.V1` |
| Capabilities | `Org.OData.Capabilities.V1` |
| Measures | `Org.OData.Measures.V1` |
| Validation | `Org.OData.Validation.V1` |
| Aggregation | `Org.OData.Aggregation.V1` |
| SAP Common (value help, labels) | `com.sap.vocabularies.Common.v1` |
| SAP UI | `com.sap.vocabularies.UI.v1` |

OASIS vocabularies: `https://github.com/oasis-tcs/odata-vocabularies`
SAP vocabularies: `https://github.com/SAP/odata-vocabularies`

## Public test services (for integration tests)

| Service | URL | Version |
|---|---|---|
| TripPin (OData reference service) | `https://services.odata.org/V4/TripPinServiceRW/` | 4.0 |
| TripPin (modifiable session) | `https://services.odata.org/TripPinRESTierService/` | 4.0 |
| Northwind V4 | `https://services.odata.org/V4/Northwind/Northwind.svc/` | 4.0 |
| Northwind V2 (regression baseline) | `https://services.odata.org/V2/Northwind/Northwind.svc/` | 2.0 |
| SAP Gateway demo (ES5) | `https://sapes5.sapdevcenter.com/sap/opu/odata/...` | 2.0, needs an account |

Integration tests must be opt-in (marker + env var), never part of the default
`make test`, so that CI does not depend on a third-party service being up.

## Reference implementations worth reading

| Project | Why |
|---|---|
| `OData/WebApi` (.NET, `Microsoft.OData.Core`) | the most complete v4 implementation; its URI parser and CSDL reader are the de-facto interpretation of ambiguous spec text |
| Olingo (`apache/olingo-odata4`, Java) | clean separation of `commons-api` / `commons-core` / `server-api` — a useful model for the shared-core / dialect split |
| `SAP/openui5` `sap.ui.model.odata.v4` | how a mature client negotiates metadata levels, `$batch`, and 4.01 |
| `tuomur/python-odata` | idiomatic Python v4 URL and payload handling |

## In-repo artefacts

| Path | Contents |
|---|---|
| `docs/v4/fixtures/trippin-v4-metadata.xml` | hand-written CSDL 4.0 exercising the constructs with no v2 analogue |
| `tests/metadata.xml` | the v2 SAP-flavoured corpus (annotations, value helps) |
| `tests/metadata_odata_org_northwind_v2.xml` | the v2 Northwind corpus |
| `tests/conftest.py::xml_builder_factory` | the metadata-skeleton builder pattern to mirror for v4 |
