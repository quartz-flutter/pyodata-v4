# Codebase audit: where the v2 assumptions live

A map of every place a protocol version is baked in, so the design can decide
what is genuinely shared, what is dialect-specific, and what is vendor-specific.
Line numbers are against commit `c8258ee`.

Classification:
- **S** — genuinely shared. Version-agnostic; a v4 implementation would want the
  identical code.
- **D** — dialect. Same *concept* in both versions, different *rendering*. The
  natural seam: shared structure, pluggable behaviour.
- **V2** — v2-only concept with no v4 counterpart. Must not be forced onto v4.
- **VENDOR** — SAP/Microsoft specific, orthogonal to the version.

---

## `pyodata/client.py` (119 lines)

| Element | Class | Note |
|---|---|---|
| `_fetch_metadata`, `_async_fetch_metadata` | **S** | HTTP GET of `$metadata` |
| `_common_fetch_metadata` content-type check | **S** | accepts `application/xml`, `atom+xml`, `text/xml` — v4 CSDL JSON would need `application/json` added |
| `Client.ODATA_VERSION_2`, `__new__` dispatch | **D** | already a dispatch point; today it raises for anything but 2. **This is where v4 plugs in.** |
| `_build_service` | **D** | hard-wired to `pyodata.v2.model.MetadataBuilder` and `pyodata.v2.service.Service` |
| namespaces/config deprecation shim | **S** | |

The dispatch skeleton already exists. Good news: the top-level seam is free.

## `pyodata/exceptions.py` (41 lines)

Entirely **S**, except `HttpError.VendorType` (**VENDOR**), a process-global
class attribute mutated by `pyodata.vendor.SAP`. v4 inherits the hierarchy as-is.

## `pyodata/vendor/SAP.py` (104 lines)

Entirely **VENDOR**. `add_btp_token_to_session` is protocol-agnostic and works
unchanged. `sap_header_error_hook` parses `sap-message` headers — also
version-agnostic. Nothing here blocks v4.

---

## `pyodata/v2/model.py` (2827 lines)

### Shared infrastructure — extractable as-is

| Lines | Element | Class |
|---|---|---|
| 36-52 | `NullAssociation`, `NullType` | **S** (`NullAssociation` is **V2**) |
| 54-86 | `ErrorPolicy`, `PolicyFatal/Warning/Ignore`, `ParserError` | **S** — v4 needs more `ParserError` members (`NAVIGATION_PROPERTY`, `ACTION`, `FUNCTION`, `SINGLETON`, `TYPE_DEFINITION`, `TERM`) |
| 89-149 | `Config` | **S** — `namespaces`, `retain_null`, error policies all carry over |
| 151-175 | `Identifier` | **S** |
| 325-344 | `TypTraits` base | **S** |
| 713-777 | `Typ`, `Collection` | **S** |
| 779-886 | `VariableDeclaration` | **S** |
| 888-963 | `Schema.Declaration` / `Declarations` | **D** — same shape, different member sets |
| 1470-1542 | `StructType`, `ComplexType` | **D** — v4 adds `BaseType`, `Abstract`, `OpenType` |
| 1544-1655 | `EnumMember`, `EnumType` | **D** — v4 makes `UnderlyingType` optional |
| 1695-1790 | `EntitySet` | **D** — v4 replaces `sap:*` capability attributes with vocabulary annotations |

### v2-only — must not be carried into v4

| Lines | Element |
|---|---|
| 2009-2061 | `EndRole` (`MULTIPLICITY_ONE/ZERO_OR_ONE/ZERO_OR_MORE`) |
| 2063-2131 | `ReferentialConstraintRole`, `PrincipalRole`, `DependentRole`, `ReferentialConstraint` (v4 has a *different* referential constraint, nested in the nav property) |
| 2133-2196 | `Association` |
| 2198-2301 | `AssociationSetEndRole`, `AssociationSet` |
| 1947-2007 | `NavigationTypeProperty` — keyed entirely on `Relationship`/`FromRole`/`ToRole` |
| 1172-1230 | `Schema.association*`, `association_set*`, `check_role_property_names` |
| 1295-1370 | the `Association` / nav-property resolution passes in `Schema.from_etree` |
| 2610-2633 | `FunctionImport.from_etree` — reads `ReturnType`/`Parameter` off the container element |
| 2636-2646 | `FunctionImportParameter.Modes` (`In`/`Out`/`InOut`) — v4 parameters are in-only |

### Dialect — same concept, different rendering

| Lines | Element | v4 difference |
|---|---|---|
| 177-269 | `Types` registry + `from_name` + `parse_type_name` | different member set; **`Types.Types` is process-global mutable state — v4 needs its own registry, not entries added to this one** |
| 346-374 | `EdmPrefixedTypTraits`, `EdmBinaryTypTraits` | v4 drops nearly all prefixes |
| 376-566 | `EdmDateTimeTypTraits`, `EdmDateTimeOffsetTypTraits`, `ms_since_epoch_to_datetime`, `parse_datetime_literal` | v4 has no `/Date(ms)/`; ISO 8601 throughout |
| 568-673 | String/Boolean/Int/LongInt/FP traits | `L`, `M`, `d`, `f` suffixes are v2-only |
| 271-323 | `EdmStructTypeSerializer` | **S** in shape |
| 676-710 | `EdmStructTypTraits`, `EnumTypTrait` | **D** — v4 enum literals are `Ns.Type'Member'` |
| 1792-1945 | `StructTypeProperty` | **VENDOR**-heavy: 18 of its properties are `sap:*` attributes. v4 sources the same information from vocabulary annotations. |
| 2303-2356 | `Annotation`, `ExternalAnnontation` | **D** — v4 annotations are a first-class, general mechanism |
| 2358-2597 | `ValueHelper`, `ValueHelperParameter` | **VENDOR** (`com.sap.vocabularies.Common.v1.ValueList`) — reusable for v4 SAP services |
| 2653-2684 | `sap_attribute_get*`, `metadata_attribute_get`, `str_to_bool` | **VENDOR** / **S** |
| 2701-2809 | `MetadataBuilder` | **D** — the whitelist, the `DataServices`/`Schema` walk and the alias mining are shared; the per-element dispatch is not |
| 2811-2827 | `schema_from_xml`, `Edmx` (deprecated) | **S** shape |

### Process-global state — a hazard for a two-dialect library

Three module-level mutable globals, all written during parsing:

1. `Types.Types` (`:186`) — the primitive type registry, lazily built, never reset.
2. `SAP_ANNOTATION_VALUE_LIST` (`:2698`) — **appended to** by
   `MetadataBuilder.update_global_variables_with_alias` on every `build()`.
3. `SAP_VALUE_HELPER_DIRECTIONS` (`:2687`) — likewise **mutated in place**.

Parsing two documents in one process already leaks aliases between them. Adding
a second dialect that writes to the same globals would turn a latent bug into a
cross-version one. **v4 must own its registries.** Fixing (2) and (3) for v2 is
a worthwhile standalone cleanup.

---

## `pyodata/v2/service.py` (1986 lines)

### Shared infrastructure — the strongest extraction candidate

| Lines | Element | Class |
|---|---|---|
| 28-31 | `urljoin` | **S** |
| 102-150 | `ODataHttpResponse` (`from_string`, `json`) | **S** |
| 232-379 | `ODataHttpRequest` — deferred request, `execute`/`async_execute`, header merge, `_build_request`, `response_hook`, cross-origin next-link guard | **S**, entirely. This is the single best piece of version-agnostic machinery in the codebase. |
| 1387-1416 | `ListWithTotalCount` | **S** |
| 1636-1653 | `EntityContainer` | **S** shape |
| 1757-1817 | `Service` accessors | **S** shape |

### Dialect

| Lines | Element | v4 difference |
|---|---|---|
| 152-229 | `EntityKey` | key *composition* is shared; the literal rendering it delegates to is not. 4.01 also allows key-as-segment. |
| 382-471 | `EntityGetRequest`, `NavEntityGetRequest` | `Accept` header value; `$expand` nesting |
| 473-560 | `EntityCreateRequest` | `X-Requested-With: X` is **VENDOR**; body shape shared; v4 adds `Prefer: return=representation` |
| 563-587 | `EntityDeleteRequest` | shared; v4 adds `If-Match` |
| 590-657 | `EntityModifyRequest` | **`MERGE` in `ALLOWED_HTTP_METHODS` is v2-only** |
| 660-776 | `QueryRequest` | `$inlinecount=allpages` -> `$count=true`; `$search`, `$apply` are new |
| 779-813 | `FunctionRequest` | v4 splits into function (GET, inline params) and action (POST, JSON body) |
| 816-1086 | `EntityProxy`, `NavEntityProxy` | `__metadata`/`etag` decode (`:839`), `results` unwrapping (`:889-895`), and **multiplicity via `EndRole` (`:875-897`) is v2-only** |
| 1088-1183 | `GetEntitySetFilter`, `FilterExpression` | operator set is shared; rendering is not |
| 1185-1344 | `GetEntitySetFilterChainable` | **the lookup DSL (`__contains`, `__in`, `__range`, ...) is excellent and version-agnostic; keep it. Only `_build_expression` (`:1288`) is dialect.** |
| 1346-1385 | `GetEntitySetRequest` | shared shape |
| 1418-1633 | `EntitySetProxy` | every handler decodes `['d']` |
| 1655-1754 | `FunctionContainer` | `_handle_response_status` is **S** and good; the decode below it is **D** |
| 1851-1911 | `create_batch`, `create_changeset` | shared shape |
| 34-99, 1914-1986 | multipart encode/decode, `MultipartRequest`, `BatchRequest`, `Changeset` | **D** — v4 4.01 adds JSON batch; the `202`-only assertion at `:1955` is too strict for v4 |

### The seven `['d']` decode sites

`:981`, `:1014`, `:1491`, `:1519`, `:1548`, `:1583`, `:1723`.

Each also hard-codes `__count` / `__next` / `results`. These are the exact
lines upstream's `experimental_v3` branch wrapped in `try/except KeyError` — see
[prior-art.md](prior-art.md) for why we are not doing that.

---

## Test suite (263 tests)

| File | Tests target | Reusable for v4? |
|---|---|---|
| `tests/test_model_v2.py` (1753 lines) | v2 CSDL parsing | No — structure-specific. Mirror it as `test_model_v4.py`. |
| `tests/test_service_v2.py` (3176 lines) | v2 request/response | No — mirror as `test_service_v4.py`. |
| `tests/test_model_v2_EdmStructTypeSerializer.py`, `..._VariableDeclaration.py` | shared abstractions | Mostly yes |
| `tests/test_vendor_sap.py`, `test_vendor_microsoft.py` | vendor hooks | Yes, unchanged |
| `tests/conftest.py` `XMLBuilder` fixture factory | v2 metadata skeleton | **Pattern is reusable** — needs a v4 sibling emitting the OASIS namespaces |
| `tests/integration/networking_libraries/` | requests/httpx/aiohttp adapters | Yes — transport is version-agnostic |

`tests/metadata.xml` and `tests/metadata_odata_org_northwind_v2.xml` are the v2
corpora. v4 needs its own: a TripPin-derived document
([`../fixtures/trippin-v4-metadata.xml`](../fixtures/trippin-v4-metadata.xml) is
the seed) and ideally a real SAP S/4HANA v4 `$metadata` sample.

---

## Summary: how much is actually shared?

Rough line accounting of the 4813 lines in `v2/model.py` + `v2/service.py`:

| Class | Approx. lines | Share |
|---|---|---|
| **S** genuinely shared | ~900 | 19% |
| **D** dialect (same concept, different rendering) | ~2400 | 50% |
| **V2** v2-only concepts | ~800 | 17% |
| **VENDOR** SAP/MS specific | ~700 | 14% |

The 19% is worth extracting and is low-risk. The 50% is where the design
question actually lives, and it is answered in
[`../plan/architecture.md`](../plan/architecture.md).
