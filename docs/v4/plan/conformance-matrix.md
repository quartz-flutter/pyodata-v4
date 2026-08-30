# Conformance matrix

Feature-by-feature tracker. Update as phases land.

Status: **done** · **wip** · **todo** · **deferred** (out of v1 scope, recorded
so it is not forgotten) · **n/a**

---

## Metadata / CSDL 4.0

| Feature | Phase | Status | Notes |
|---|---|---|---|
| `edmx:Edmx@Version` detection | 1 | todo | also the v2-side "this is v4" error |
| EDMX/EDM namespace recognition | 1 | todo | namespaces already whitelisted — that is the bug |
| `EntityType`, `Key`, `PropertyRef` | 3 | todo | |
| `EntityType@BaseType` inheritance | 3 | todo | today: silent property loss |
| `EntityType@Abstract` / `@OpenType` / `@HasStream` | 3 | todo | |
| `ComplexType` incl. `BaseType` | 3 | todo | |
| `NavigationProperty` `Type`/`Nullable`/`Partner` | 3 | todo | replaces `Association` entirely |
| `NavigationProperty@ContainsTarget` (containment) | 3 | todo | |
| nested `ReferentialConstraint` | 3 | todo | different element from v2's |
| `EntitySet` + `NavigationPropertyBinding` | 3 | todo | required for `.nav()` |
| `Singleton` | 3 | todo | |
| `EnumType` (optional `UnderlyingType`, `IsFlags`) | 3 | todo | |
| `TypeDefinition` | 3 | todo | |
| `Term` declarations | 3 | todo | |
| schema-level `Function` (`IsBound`, `IsComposable`, `EntitySetPath`) | 3 | todo | |
| schema-level `Action` (`IsBound`) | 3 | todo | |
| operation overload resolution by signature | 3 | todo | |
| `FunctionImport@Function`, `ActionImport@Action` | 3 | todo | today: signature silently lost |
| inline `Annotation` on any element | 3 | todo | |
| external `Annotations@Target` groups | 3 | todo | v2 supports a narrow SAP subset |
| `Record` / `PropertyValue` / `Collection` annotation values | 3 | todo | |
| `edmx:Reference` / `Include` / `IncludeAnnotations` | 3 | todo | v2 mines these for SAP aliases only |
| `Org.OData.Core.V1` terms | 3 | todo | `Description`, `Computed`, `Immutable` |
| `Org.OData.Capabilities.V1` terms | 3 | todo | maps onto v2's `sap:creatable/updatable/...` surface |
| `Org.OData.Measures.V1` terms | 3 | todo | |
| `com.sap.vocabularies.Common.v1` (value help, labels) | 3 | todo | reuse the existing `ValueHelper` machinery |
| CSDL **JSON** representation (4.01) | — | deferred | XML first |

## Primitive types

| Type | Phase | Status | Notes |
|---|---|---|---|
| `String Boolean Byte SByte Int16 Int32 Int64 Single Double Decimal Guid Binary` | 3 | todo | **v4 literal forms — no `L`/`M`/`d`/`f` suffixes, no `guid'` prefix** |
| `DateTimeOffset` | 3 | todo | ISO 8601, never `/Date(ms)/` |
| `Date` | 3 | todo | new in v4 |
| `TimeOfDay` | 3 | todo | new in v4 |
| `Duration` | 3 | todo | replaces v2 `Edm.Time` |
| `Stream` | — | deferred | |
| `Geography*` / `Geometry*` | — | deferred | |
| `DateTime`, `Time`, `Float` | — | n/a | removed in v4; stay v2-only |

## URL conventions

| Feature | Phase | Status |
|---|---|---|
| `EntitySet(key)` with v4 literal rendering | 4 | todo |
| composite keys `(a=1,b='x')` | 4 | todo |
| key-as-segment `EntitySet/key` (4.01) | — | deferred |
| navigation segments | 4 | todo |
| `$value` | 4 | todo |
| `$count` path segment | 5 | todo |
| `$ref` (replaces v2 `$links`) | 5 | todo |
| type-cast segments `/People/Ns.Manager` | 5 | todo |
| unbound function `Fn(p=1)` | 5 | todo |
| bound function `Set(k)/Ns.Fn(p=1)` | 5 | todo |
| unbound / bound action (POST + JSON body) | 5 | todo |
| parameter aliases `Fn(p=@a)?@a=...` | 5 | todo |
| composable function chaining | — | deferred |

## Query options

| Option | Phase | Status | Notes |
|---|---|---|---|
| `$top` `$skip` `$select` `$orderby` `$filter` `$format` | 4 | todo | |
| `$expand` (flat) | 4 | todo | |
| `$expand` nested options (`$select`/`$filter`/`$top`/`$expand`) | 4 | todo | |
| `$expand=*`, `/$ref`, `/$count` | 5 | todo | |
| `$count=true` | 4 | todo | replaces `$inlinecount=allpages` |
| `$search` | 4 | todo | |
| `$skiptoken` / server paging via `@odata.nextLink` | 4 | todo | |
| `$apply` (`groupby`/`aggregate`/`filter`/`topcount`/`compute`) | 5 | todo | |
| `$compute`, `$index` (4.01) | — | deferred | |

## `$filter` expressions

| Feature | Phase | Status | Notes |
|---|---|---|---|
| `eq ne lt le gt ge and or not` | 4 | todo | |
| arithmetic incl. `divby` | 4 | todo | |
| `contains(field, value)` | 4 | todo | **argument order reversed vs v2 `substringof`** |
| `startswith` / `endswith` | 4 | todo | bare boolean, no `eq true` |
| string functions incl. `matchesPattern` | 4 | todo | |
| date functions incl. `now()`, `fractionalseconds` | 4 | todo | |
| lambda `any()` / `all()` | 5 | todo | |
| `in` (4.01) | 5 | todo | maps to the existing `__in` lookup |
| `has` (enum flags) | 5 | todo | |
| `cast` / `isof` | — | deferred | |
| `geo.*` | — | deferred | |
| **lookup DSL preserved unchanged** (`__contains`, `__startswith`, `__gt`, `__range`, `__in`, `__length`) | 4 | todo | interface identical to v2, rendering differs |

## Payloads

| Feature | Phase | Status |
|---|---|---|
| entity without `d` envelope | 4 | todo |
| collection under `value` | 4 | todo |
| `@odata.count` / `@count` | 4 | todo |
| `@odata.nextLink` / `@nextLink` | 4 | todo |
| `@odata.etag`, `@odata.id`, `@odata.type` | 4 | todo |
| `Prop@odata.navigationLink` | 4 | todo |
| expanded to-many as a bare array | 4 | todo |
| `odata.metadata=none/minimal/full` negotiation | 4 | todo |
| Int64/Decimal as string, `IEEE754Compatible` | 4 | todo |
| v4 error body (`message` is a string) | 4 | todo |
| delta payloads | — | deferred |

## HTTP semantics

| Feature | Phase | Status |
|---|---|---|
| `OData-Version` / `OData-MaxVersion` headers | 4 | todo |
| `Accept: application/json;odata.metadata=minimal` | 4 | todo |
| `PATCH` only (no `MERGE`) | 4 | todo |
| no `X-Requested-With` default | 4 | todo |
| `If-Match` from ETag | 4 | todo |
| `Prefer: return=representation` / `minimal` | 4 | todo |
| `OData-EntityId` on 204 create | 4 | todo |
| multipart `$batch` (4.0), accepting 200 or 202 | 5 | todo |
| JSON `$batch` (4.01) with `id` / `dependsOn` | 5 | todo |
| changesets / `atomicityGroup` | 5 | todo |
| `Prefer: respond-async` + 202 polling | — | deferred |
| v4 JSON service document | 5 | todo |

---

## v2 capabilities that need a v4 equivalent

Every one of these is why people use this library. A v4 client without them is
a downgrade, not a port.

| Capability | v2 mechanism | v4 mechanism | Phase | Status |
|---|---|---|---|---|
| Per-category parser error policies | `Config` + `ParserError` | same, extended enum | 3 | todo |
| Permissive parsing of broken metadata | `NullType` + `Schema.is_valid` | same | 3 | todo |
| Property labels | `sap:label` | `Core.Description` / `Common.Label` | 3 | todo |
| creatable/updatable/sortable/filterable | `sap:*` attributes | `Capabilities.V1` terms | 3 | todo |
| Value help | `com.sap.vocabularies.Common.v1.ValueList` | same vocabulary, v4 annotation syntax | 3 | todo |
| SAP BTP auth | `vendor/SAP.py` | unchanged | — | n/a |
| `sap-message` error headers | `sap_header_error_hook` | unchanged | — | n/a |
| Batch + changesets | multipart | multipart + JSON batch | 5 | todo |
| Async execution | `async_execute` | shared via `core/http.py` | 2 | todo |
| `response_hook` | `ODataHttpRequest` | shared via `core/http.py` | 2 | todo |
| URL-only usage (Locust pattern) | `get_path`/`get_query_params` | same getters | 4 | todo |
| `retain_null` | `Config.retain_null` | same | 3 | todo |
| Static metadata | `Client(metadata=...)` | same | 1 | todo |
| Cross-origin next-link rejection | `_build_request` | shared via `core/http.py` | 2 | todo |

---

## v2 regression guards

| Guard | Phase | Status |
|---|---|---|
| G1 public API snapshot | 0 | todo |
| G2 v2 wire-format golden tests | 0 | todo |
| G3 cross-version isolation (parse v2 and v4 in one process, both orders) | 3 | todo |
| G4 CI matrix 3.10–3.14 × lxml 4.6.5–6.1.1 | 6 | todo |
| OASIS ABNF test corpus vendored (`tests/fixtures/v4/`) | 0 | todo |
| ABNF corpus runs green over the v4 literal/URL builders | 4 | todo |
| Baseline held: ≥263 tests, ≥91% total coverage | all | **holding** |
| `pylint` runnable on Python ≥3.11 | 0 | todo |
| v2 defect: enum range check `<` -> `<=` (`model.py:1634`) | 1 | todo |
| v2 defect: `__range` emits `gte`/`lte` -> `ge`/`le` (`service.py:1329`) | 1 | todo |
| v2 defect: global alias lists mutated per `build()` | 2 | todo |
