# Resource bibliography

## OData v4 — normative specifications (OASIS)

The 4.01 versions are current; 4.0 is what most deployed services (including SAP
S/4HANA) actually emit. Implement against 4.0 and accept 4.01 extensions.

| Document | URI |
|---|---|
| OData Version 4.01 Part 1: Protocol | `https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part1-protocol.html` |
| OData Version 4.01 Part 2: URL Conventions | `https://docs.oasis-open.org/odata/odata/v4.01/odata-v4.01-part2-url-conventions.html` |
| OData Version 4.01 Part 3: CSDL (concepts) | `https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/odata-csdl-xml-v4.01.html` |
| OData CSDL **XML** Representation 4.01 | `https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/odata-csdl-xml-v4.01.html` |
| OData CSDL **JSON** Representation 4.01 | `https://docs.oasis-open.org/odata/odata-csdl-json/v4.01/odata-csdl-json-v4.01.html` |
| OData **JSON Format** 4.01 | `https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html` |
| OData Extension for Data Aggregation (`$apply`) 4.0 | `https://docs.oasis-open.org/odata/odata-data-aggregation-ext/v4.0/odata-data-aggregation-ext-v4.0.html` |
| OData 4.0 (errata 03) Part 1–3 | `https://docs.oasis-open.org/odata/odata/v4.0/odata-v4.0-part1-protocol.html` |
| ABNF grammars (`odata-abnf-construction-rules.txt`) | `https://docs.oasis-open.org/odata/odata/v4.01/csprd06/abnf/` |

> **Note for this sandbox:** `docs.oasis-open.org` and `www.odata.org` are
> blocked by the network egress proxy. The URIs above are recorded for use
> outside the sandbox. When a normative detail is needed and cannot be fetched,
> encode the assumption as a test with a comment naming the spec section, so it
> is auditable later rather than invisible.

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
