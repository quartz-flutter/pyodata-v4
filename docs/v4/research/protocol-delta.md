# OData v2 -> v4: the delta that matters to this client

Scoped to what `pyodata` actually does: parse CSDL, build URLs, serialise and
deserialise JSON, and batch. Ordered by the layer it lands in.
Canonical specs are listed in [resources.md](resources.md).

Legend: **B** = breaking for existing code · **N** = new capability with no v2
analogue · **=** = unchanged.

---

## 1. Metadata / CSDL

### Namespaces and versioning

| | v2 | v4 |
|---|---|---|
| EDMX namespace | `http://schemas.microsoft.com/ado/2007/06/edmx` | `http://docs.oasis-open.org/odata/ns/edmx` |
| EDM namespace | `http://schemas.microsoft.com/ado/{2006/04,2007/05,2008/09,2009/11}/edm` | `http://docs.oasis-open.org/odata/ns/edm` |
| `edmx:Edmx/@Version` | `1.0` | `4.0` or `4.01` |
| Version marker | `edmx:DataServices/@m:DataServiceVersion="2.0"` | `@Version` on `edmx:Edmx` |

**B.** Both v4 namespaces are already whitelisted in
`MetadataBuilder` — see [parser-behaviour-v4-input.md](parser-behaviour-v4-input.md).
The `@Version` attribute is the reliable discriminator and is currently unread.

### Relationships — the deepest structural break

| v2 | v4 |
|---|---|
| `<Association>` + `<End Role Type Multiplicity>` + `<ReferentialConstraint><Principal/><Dependent/></ReferentialConstraint>` | **Removed entirely** |
| `<AssociationSet>` + `<End Role EntitySet>` in the container | **Removed entirely** |
| `<NavigationProperty Name Relationship FromRole ToRole>` | `<NavigationProperty Name Type Nullable Partner ContainsTarget>` with nested `<ReferentialConstraint Property ReferencedProperty>` |
| target entity set derived from `AssociationSet` | `<EntitySet><NavigationPropertyBinding Path Target/></EntitySet>` |
| multiplicity from `End/@Multiplicity` (`1`, `0..1`, `*`) | from the property's own `Type`: `Collection(Ns.T)` vs `Ns.T`, plus `Nullable` |

**B, structural.** `Association`, `AssociationSet`, `EndRole`,
`PrincipalRole`, `DependentRole`, `NullAssociation`, `Schema.association*()`,
`NavigationTypeProperty.to_role` and `EntityProxy.nav()` are all v2-only
concepts. v4 navigation must be modelled directly on the navigation property.
This alone rules out sharing the model object graph between versions.

### Operations

| v2 | v4 |
|---|---|
| `<FunctionImport Name ReturnType EntitySet m:HttpMethod>` in the container, with `<Parameter Mode="In">` children | signature moves to schema level: `<Function Name IsBound IsComposable EntitySetPath>` / `<Action Name IsBound EntitySetPath>` with `<Parameter Type Nullable>` and an explicit `<ReturnType Type Nullable>` element |
| container entry does everything | container holds only `<FunctionImport Name Function EntitySet IncludeInServiceDocument>` and `<ActionImport Name Action EntitySet>` |
| HTTP verb from a vendor attribute | **`Function` is always GET and side-effect-free; `Action` is always POST.** No verb attribute. |
| no overloads | overloads by parameter signature; `IsBound` operations take the binding parameter first |
| — | **N** composable functions (`IsComposable`) chain into further path segments |

**B.** `FunctionImport.from_etree` and `FunctionRequest` need a v4 counterpart
that resolves the container entry to its schema-level definition.

### Type system additions

| v4 construct | v2 analogue |
|---|---|
| `<Singleton Name Type>` | **N** — none |
| `<TypeDefinition Name UnderlyingType>` | **N** — none |
| `<Term>` (annotation term declarations) | **N** — none |
| `BaseType` on `EntityType` / `ComplexType` | **N** — v2 has no inheritance in practice |
| `Abstract`, `OpenType`, `HasStream` on `EntityType` | **N** |
| `<EnumType>` `UnderlyingType` optional (defaults `Edm.Int32`) | required in this parser |
| inline `<Annotation Term Qualifier>` on any element | v2 uses vendor attributes (`sap:label`, `sap:creatable`, ...) and external `<Annotations>` groups |
| `<edmx:Reference Uri>` / `<edmx:Include Namespace Alias>` / `<edmx:IncludeAnnotations>` | present but only mined for SAP value-list aliases |
| `<Key><PropertyRef Name Alias/></Key>` (alias for nested key paths) | `Name` only |
| CSDL **JSON** representation (4.01) | **N** — v2 is XML only |

### Primitive types

Removed in v4: `Edm.DateTime`, `Edm.Time`, `Edm.Float`.
Added in v4: `Edm.Date`, `Edm.TimeOfDay`, `Edm.Duration`, `Edm.Stream`,
`Edm.Geography*` / `Edm.Geometry*`.
Unchanged: `Binary Boolean Byte Decimal Double Guid Int16 Int32 Int64 SByte Single String DateTimeOffset`.

`Edm.DateTimeOffset` becomes the general timestamp type; v2's `Edm.DateTime`
(timezone-naive) has no v4 equivalent. `Edm.Duration` replaces `Edm.Time`.

**B.** `Types._build_types()` (`pyodata/v2/model.py:188-214`) is a v2 registry:
wrong members, and — see below — wrong literal forms.

---

## 2. URL literals — every prefix and suffix is gone

This is the largest single source of silent wrongness, because a v2 literal is
*syntactically valid text* that a v4 server will simply reject or misread.

| Type | v2 literal | v4 literal |
|---|---|---|
| `Edm.String` | `'O''Brien'` | `'O''Brien'` **=** |
| `Edm.DateTime` | `datetime'2000-01-01T00:00'` | type removed |
| `Edm.DateTimeOffset` | `datetimeoffset'2000-01-01T00:00:00Z'` | `2000-01-01T00:00:00Z` |
| `Edm.Date` | — | `2000-01-01` |
| `Edm.TimeOfDay` | — | `13:20:00` |
| `Edm.Duration` | `time'PT1H'` | `duration'PT1H'` (prefix optional in 4.01) |
| `Edm.Guid` | `guid'0000...'` | `0000...` (bare) |
| `Edm.Binary` | `binary'0FAB'` / `X'0FAB'` (hex content) | `binary'T0RhdGE'` — prefix kept, **content is base64url**, and the v2 `X'...'` form is invalid (ABNF `binaryLiteral`; the OASIS corpus has a negative vector rejecting `X'1a2B3c4D'`) |
| `Edm.Int64` | `123L` | `123` |
| `Edm.Decimal` | `1.5M` | `1.5` |
| `Edm.Double` | `1.5d` | `1.5` |
| `Edm.Single` | `1.5f` | `1.5` |
| enum member | — | `Ns.Colour'Red'` or `Ns.Colour'Red,Green'` for flags |

**B.** `EdmPrefixedTypTraits` and every `Typ(..., null_value=...)` default in
`Types._build_types` encode the v2 forms. `EntityKey.to_key_string()` composes
them straight into the path, so **every single-key GET/PATCH/DELETE URL this
library builds is wrong for v4** unless the traits are dialect-scoped.

---

## 3. Resource paths

| | v2 | v4 |
|---|---|---|
| by key | `People('russell')` | `People('russell')`, and `People/russell` (key-as-segment, 4.01) |
| navigation | `People('x')/Trips` | **=** |
| entity reference | `$links` | `$ref` **B** |
| raw value | `$value` | **=** |
| count | `/$count` segment | `/$count` segment **and** `$count=true` option |
| type cast | — | `/People/Ns.Manager`, `/People('x')/Ns.Manager/Budget` **N** |
| singleton | — | `/Me`, `/Me/Trips` **N** |
| unbound function | `/GetX?p=1` (as function import, verb varies) | `/GetX(p=1)` |
| bound function | — | `/People('x')/Ns.GetFriends(n=2)` — **namespace-qualified** **N** |
| action | — | `POST /People('x')/Ns.ShareTrip` with JSON parameter body **N** |
| parameter alias | — | `/GetX(p=@v)?@v='abc'` **N** |

---

## 4. System query options

| Option | v2 | v4 |
|---|---|---|
| `$filter` `$select` `$orderby` `$top` `$skip` `$expand` `$format` | yes | **=** |
| `$inlinecount=allpages` | yes | **removed** -> `$count=true` **B** |
| `$skiptoken` | server-generated | **=** |
| `$search` | — | **N** free-text search |
| `$apply` | — | **N** aggregation: `groupby`, `aggregate`, `filter`, `topcount`, `compute` |
| `$expand` nested options | not supported | **N** `$expand=Trips($select=Name;$filter=...;$top=5;$expand=...)`, `$expand=*`, `$expand=Trips/$ref`, `$expand=Trips/$count` |
| `$select` | property names | **N** also `*`, `Ns.Type/Prop` casts, `Addr/City` paths |
| `$compute` | — | **N** (4.01) |
| `$index` | — | **N** (4.01) |

### `$filter` expression language

| | v2 | v4 |
|---|---|---|
| comparison | `eq ne lt le gt ge` | **=** |
| logical | `and or not` | **=** |
| arithmetic | `add sub mul div mod` | **=** plus `divby` (4.01) |
| substring test | `substringof(sub, str) eq true` | **`contains(str, sub)`** — different name **and reversed argument order** **B** |
| prefix/suffix | `startswith(str, sub)` / `endswith` | **=** |
| string fns | `length indexof replace substring tolower toupper trim concat` | **=** plus `matchesPattern` (4.01) |
| date fns | `year month day hour minute second` | **=** plus `fractionalseconds totaloffsetminutes date time mindatetime maxdatetime now` |
| math | `round floor ceiling` | **=** |
| type fns | `isof cast` | **=** |
| lambda | — | **N** `Trips/any(t: t/Budget gt 1000)`, `Trips/all(...)` |
| `in` | — | **N** (4.01) `Name in ('a','b')` |
| `has` | — | **N** enum flag test |
| geo | — | **N** `geo.distance`, `geo.intersects`, `geo.length` |

**B.** `GetEntitySetFilterChainable._build_expression`
(`pyodata/v2/service.py:1288-1338`) hard-codes `substringof(value, field) eq true`
for the `__contains` lookup. In v4 that function does not exist. The lookup DSL
(`__contains`, `__startswith`, `__in`, `__range`, ...) is a good user-facing API
and should be preserved verbatim in v4 — only its *rendering* changes.

---

## 5. JSON payloads

| | v2 (JSON verbose) | v4 (JSON) |
|---|---|---|
| single entity | `{"d": { ...props... }}` | `{ "@odata.context": "...", ...props... }` — no envelope |
| collection | `{"d": {"results": [...]}}` | `{"@odata.context": "...", "value": [...]}` |
| count | `"__count": "42"` (string) | `"@odata.count": 42` (number); `"@count"` in 4.01 |
| next page | `"__next": "https://..."` | `"@odata.nextLink": "..."`; `"@nextLink"` in 4.01 |
| entity identity/type/etag | `"__metadata": {"uri","type","etag"}` | `"@odata.id"`, `"@odata.type"`, `"@odata.etag"` |
| unexpanded navigation | `"Prop": {"__deferred": {"uri": "..."}}` | `"Prop@odata.navigationLink": "..."`, or omitted |
| expanded to-many | `"Prop": {"results": [...]}` | `"Prop": [...]` |
| expanded to-one | `"Prop": {...}` | **=** |
| `Edm.DateTime` | `"/Date(946684800000)/"` | type removed |
| `Edm.DateTimeOffset` | `"/Date(946684800000+0)/"` or ISO | `"2000-01-01T00:00:00Z"` ISO 8601 |
| `Edm.Int64` / `Edm.Decimal` | JSON string | string by default; number when `IEEE754Compatible=false` is negotiated |
| error body | `{"error":{"code":"..","message":{"lang":"en","value":".."}}}` | `{"error":{"code":"..","message":"..","target":"..","details":[..],"innererror":{..}}}` — **`message` is a plain string** **B** |
| metadata volume | fixed | negotiated: `odata.metadata=none\|minimal\|full` |

**B.** `response.json()['d']` appears at seven call sites in
`pyodata/v2/service.py` (`:981`, `:1014`, `:1491`, `:1519`, `:1548`, `:1583`,
`:1723`). Each is a v2-only decode.

---

## 6. HTTP semantics

| | v2 | v4 |
|---|---|---|
| version request header | `MaxDataServiceVersion: 2.0` | `OData-MaxVersion: 4.0` |
| version response header | `DataServiceVersion: 2.0` | `OData-Version: 4.0` |
| Accept | `application/json` | `application/json;odata.metadata=minimal` |
| update verb | `MERGE` (v2) or `PATCH` | **`PATCH` only — `MERGE` is removed** **B** |
| response to POST/PATCH | 201/204, body varies | 204 by default; `Prefer: return=representation` -> 200 + body; `Prefer: return=minimal` -> 204 |
| new entity id on 204 | — | `OData-EntityId` response header **N** |
| concurrency | ETag, `If-Match` | **=**, but mandatory where an ETag is defined |
| async | — | `Prefer: respond-async` + 202 + `Location` polling **N** |
| CSRF | SAP-specific `X-CSRF-Token` | unchanged (still vendor territory) |

**B.** `EntityModifyRequest.ALLOWED_HTTP_METHODS` includes `MERGE`; v4 must not.
`EntityCreateRequest.get_default_headers()` sends `X-Requested-With: X`, an SAP
NetWeaver Gateway quirk that must not become a v4 default.

---

## 7. Batch

| | v2 | v4 4.0 | v4 4.01 |
|---|---|---|---|
| format | `multipart/mixed` | `multipart/mixed` | **also JSON** (`{"requests":[...]}`) **N** |
| changesets | `multipart/mixed` nested | **=** | `"atomicityGroup"` |
| request correlation | `Content-ID` | `Content-ID`, referencable as `$1` in later URLs | `"id"` / `"dependsOn"` |
| response code | 202 Accepted | 200 OK is also valid | 200 OK |

`MultipartRequest.http_response_handler` hard-asserts `202`
(`pyodata/v2/service.py:1955`). v4 servers commonly answer `200`.

---

## 8. Service document

| v2 | v4 |
|---|---|
| AtomPub XML at the service root | JSON: `{"@odata.context":".../$metadata","value":[{"name":"People","kind":"EntitySet","url":"People"}]}` |

Neither is currently consumed by this client — it goes straight to `$metadata`.
Worth adding for v4 because `kind` distinguishes `EntitySet`, `Singleton`,
`FunctionImport` and `ServiceDocument`.
