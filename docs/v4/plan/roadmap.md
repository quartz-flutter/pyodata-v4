# Roadmap

Eight phases. Each has a deliverable and an exit criterion that can be checked,
not judged. Phases 0–1 de-risk; 2–5 build; 6–7 finish.

Effort is given in "sessions" (a focused unit of work), not calendar time.

---

## Phase 0 — Safety net  *(~2 sessions)*

Nothing about v4. This is what makes every later phase safe.

1. Fix the local toolchain: `dev-requirements.txt` pins `pylint==2.8.3`, whose
   `wrapt` dependency does not build on Python ≥3.11, so `make lint` / `make
   check` are unrunnable on a current interpreter. Unpin or raise, and fix
   whatever new warnings appear.
2. **G1 — public API snapshot test** (`tests/test_public_api_snapshot.py` +
   a checked-in JSON snapshot). Enumerates public names and signatures across
   every module. This is the tripwire for rule R3.
3. **G2 — v2 wire-format golden tests**. Pin `get_method/get_path/
   get_query_params/get_body/get_headers` for every request class, every
   `Edm.*` literal and `null_value`, every `$filter` lookup rendering,
   `EntityKey.to_key_string()`, and the multipart batch body. See
   [compatibility-contract.md](compatibility-contract.md) G2.
4. Record the baseline in CI so a coverage regression fails the build.
5. Vendor the normative reference material into the repo, pinned by commit:
   `abnf/odata-abnf-construction-rules.txt` and `abnf/odata-abnf-testcases.yaml`
   from `oasis-tcs/odata-abnf` into `tests/fixtures/v4/`, and the OASIS + SAP
   vocabulary CSDL documents. See
   [../research/resources.md](../research/resources.md). Pinned copies, never
   fetched at test time.

**Exit:** `make check` runs clean on Python 3.11+. Test count > 263. The golden
tests fail loudly if any v2 byte on the wire changes. The ABNF corpus is in the
tree and readable by the test suite.

---

## Phase 1 — Version detection, and an honest v4 error  *(~1 session)*

User-visible value on day one, with no v4 implementation behind it.

1. `MetadataBuilder` reads `edmx:Edmx/@Version`. A `4.0`/`4.01` document hitting
   the v2 parser raises
   `PyODataParserError('OData 4.0 metadata detected; pyodata v2 cannot parse it — pass odata_version=4')`
   instead of today's baffling
   `Type None is not valid as underlying type for EnumType`.
2. `Client` gains `odata_version=None` meaning auto-detect, per
   [architecture.md](architecture.md#version-detection-and-dispatch).
   `odata_version=2` continues to take **exactly** today's path.
3. Fix the two pre-existing v2 defects found during the audit, each in its own
   commit with its own test:
   - `model.py:1634` — enum member range check uses `<` where it needs `<=`,
     wrongly rejecting boundary values.
   - `service.py:1329` — `__range` lookup emits `gte`/`lte`, which are not
     OData operators in any version; must be `ge`/`le`.

**Exit:** feeding `docs/v4/fixtures/trippin-v4-metadata.xml` to
`pyodata.Client` produces an actionable error naming the version. Both defect
fixes have regression tests. Baseline suite still green.

---

## Phase 2 — Extract `pyodata/core/`  *(~3 sessions)*

Pure moves. One module per commit. Full suite green after each.

| Commit | Moves into `core/` | Re-exported from |
|---|---|---|
| 1 | `Config`, `ErrorPolicy`, `Policy*`, `ParserError` -> `core/config.py` | `pyodata.v2.model` |
| 2 | `Identifier`, `TypeInfo`, `IdentifierInfo` -> `core/identifier.py` | `pyodata.v2.model` |
| 3 | `TypTraits`, `Typ`, `Collection`, `VariableDeclaration`, `EdmStructTypeSerializer` -> `core/typ.py` | `pyodata.v2.model` |
| 4 | `urljoin`, `ODataHttpResponse`, `ODataHttpRequest`, `ListWithTotalCount` -> `core/http.py` | `pyodata.v2.service` |
| 5 | the lookup DSL from `GetEntitySetFilterChainable`, with `_build_expression` left abstract -> `core/lookups.py` | `pyodata.v2.service` |

Note what is **not** moved: the concrete `Edm*TypTraits` subclasses stay in
`v2/`, because their literal forms are v2-specific. Only the `TypTraits` base
class is shared.

**Exit:** `pyodata/core/` exists; `git diff` shows no behaviour change; API
snapshot unchanged; 263+ tests green; coverage not down.

---

## Phase 3 — `pyodata/v4/model.py`: the CSDL 4.0 parser  *(~5 sessions)*

The largest phase. Build it against
[`../fixtures/trippin-v4-metadata.xml`](../fixtures/trippin-v4-metadata.xml)
and extend that fixture as coverage grows.

1. `v4/traits.py` — the v4 `Edm` registry with **v4 literal forms** (no
   `datetime'`/`guid'` prefixes, no `L`/`M`/`d`/`f` suffixes), plus `Edm.Date`,
   `Edm.TimeOfDay`, `Edm.Duration`. Its own registry object, not `Types.Types`
   (rule R5).
2. `EntityType` / `ComplexType` with `BaseType` resolution (inherited properties
   and keys), `Abstract`, `OpenType`, `HasStream`.
3. `NavigationProperty`: `Type` (collection vs single), `Nullable`, `Partner`,
   `ContainsTarget`, nested `<ReferentialConstraint Property ReferencedProperty>`.
   **No `Association` anywhere.**
4. `EntitySet` + `<NavigationPropertyBinding Path Target>` — this is what makes
   `.nav()` possible in v4.
5. `EnumType` with optional `UnderlyingType` (default `Edm.Int32`), `IsFlags`.
6. `TypeDefinition`, `Singleton`, `Term`.
7. Schema-level `Function` / `Action` with `IsBound`, `IsComposable`,
   `EntitySetPath`, `<ReturnType>`, and overload resolution by parameter
   signature; container `FunctionImport` / `ActionImport` resolving to them.
8. Vocabulary annotations: inline `<Annotation Term Qualifier>` on any element
   and external `<Annotations Target>` groups, with `<Record>`/`<PropertyValue>`/
   `<Collection>` values. Map `Org.OData.Core.V1`, `Capabilities.V1`,
   `Measures.V1` and `com.sap.vocabularies.*` onto the same
   `label`/`creatable`/`updatable`/`filterable`/value-help surface that v2
   exposes via `sap:*` attributes, so both dialects present one API.
9. Route every parse failure through `config.err_policy(...)` with new
   `ParserError` members, preserving the permissive-parsing behaviour that makes
   this library usable against real enterprise metadata.

**Exit:** the TripPin fixture parses with `PolicyFatal` and no warnings. Every
construct in the phase-3 list is asserted in `tests/test_model_v4.py`. The G3
isolation test passes. ≥90% coverage on `pyodata/v4/model.py`.

---

## Phase 4 — `pyodata/v4/service.py`: requests and payloads  *(~4 sessions)*

1. Version headers: `OData-Version: 4.0`, `OData-MaxVersion: 4.0`,
   `Accept: application/json;odata.metadata=minimal`. **No `X-Requested-With`**
   (SAP-only). Drop `MERGE` from the allowed update verbs.
2. JSON decoding: no `d` envelope; `value` for collections; `@odata.count`,
   `@odata.nextLink`, `@odata.etag`, `@odata.id`, `@odata.type`,
   `Prop@odata.navigationLink`; accept the 4.01 short forms (`@count`,
   `@nextLink`). ISO 8601 timestamps, never `/Date(ms)/`.
3. Error bodies: v4 `message` is a plain string, not `{"lang","value"}`.
4. Query options: `$count=true` replacing `$inlinecount=allpages`; `$search`;
   nested `$expand` options; `$select` with paths and `*`.
5. `$filter` rendering for the shared lookup DSL: `contains(field, value)` —
   note the reversed argument order versus v2's `substringof(value, field)`.
   Add `any`/`all` lambdas and the 4.01 `in` operator.
6. Navigation via `NavigationPropertyBinding`, replacing the `AssociationSet`
   lookup in `EntityProxy.nav()`.
7. CUD: `PATCH` only; `If-Match` from the entity ETag; `Prefer:
   return=representation` and the `OData-EntityId` header on a 204 create.

**Exit:** `tests/test_service_v4.py` mirrors the shape of `test_service_v2.py`
for every operation, using `responses`. Golden tests pin every v4 URL and body.
The ABNF test corpus vendored in phase 0 runs as a parametrized suite. It is a
*parsing* corpus (`Rule` + `Input`, `FailAt` for negatives), so use it in the
directions where it actually applies: positive vectors for the literal rules
(`primitiveLiteral`, `keyPredicate`, per-type literal rules) feed
`from_literal`/round-trip assertions; negative vectors are must-reject inputs
and must-never-produce outputs for the renderers (they are what catch
over-permissive escaping — e.g. the corpus rejects the v2 binary form
`X'1a2B3c4D'`). Validating *generated* full URLs against the `odataUri` grammar
needs an ABNF engine; that is allowed as a **test-only** dependency (the
lxml-only rule binds runtime deps), or skipped in favour of the golden URL
tests. ≥90% coverage on `pyodata/v4/service.py`.

---

## Phase 5 — v4-native features  *(~3 sessions)*

The things v2 simply cannot do, added as new API surface (never by overloading
v2 names):

1. `service.singletons.Me` — singleton access.
2. `service.functions.X(p=1)` (GET, inline parameters, parameter aliases) and
   `service.actions.Y()` (POST, JSON parameter body).
3. Bound operations: `entity.action('Ns.ShareTrip')`,
   `entity.function('Ns.GetFriends')` — namespace-qualified, per spec.
4. `$ref` (entity references) replacing v2's `$links`; `$count` as a path
   segment; type-cast segments (`/People/Ns.Manager`).
5. `$apply` aggregation: `groupby`, `aggregate`, `filter`, `topcount`, `compute`.
6. Batch: multipart for 4.0 **and** JSON batch for 4.01, with `Content-ID`/`id`
   correlation and `dependsOn`. Accept `200` as well as `202`.
7. The v4 JSON service document (`kind` distinguishes EntitySet / Singleton /
   FunctionImport).

**Exit:** each feature has unit tests; the conformance matrix's "v1 scope" column
is fully green.

---

## Phase 6 — Integration and hardening  *(~2 sessions)*

1. Opt-in integration tests (pytest marker + env var, excluded from `make test`)
   against TripPin v4 and Northwind V2 — the latter proving v2 still works
   end-to-end against a live service.
2. Real SAP S/4HANA v4 `$metadata` sample added to the corpus, if one can be
   obtained; otherwise a synthesised equivalent exercising
   `com.sap.vocabularies.*`.
3. Error-policy behaviour verified for deliberately malformed v4 metadata, the
   way `test_model_v2.py` does for v2.
4. CI matrix (3.10–3.14 × lxml 4.6.5–6.1.1) green on the v4 code.

**Exit:** CI green across the matrix; integration suite passes on demand.

---

## Phase 7 — Documentation and release  *(~2 sessions)*

1. `README.md` and `docs/index.rst`: "Supported features — OData V2, OData V4".
2. New `docs/usage/odata_v4.rst` and a v2↔v4 differences page derived from
   [../research/protocol-delta.md](../research/protocol-delta.md).
3. Update every `docs/usage/*.rst` page with a v4 example alongside the v2 one.
4. `CHANGELOG.md`: the v4 addition, and an explicit statement that v2 behaviour
   is unchanged, with the two defect fixes from phase 1 listed separately.
5. Mark `pyodata.core` provisional/internal until 2.0.
6. Version bump; decide whether this fork publishes under a distinct
   distribution name.

**Exit:** the [definition of done](compatibility-contract.md#definition-of-done-for-the-whole-project)
is met in full.

---

## Sequencing notes

- **Phases 0 and 1 are worth doing even if the project stops there.** They leave
  v2 better tested, better linted, two bugs lighter, and no longer capable of
  silently mangling a v4 document.
- Phase 2 is the only phase that touches v2 code at scale. It is deliberately
  isolated, mechanical, and guarded by phase 0's gates. If it goes badly, it
  reverts cleanly and phase 3 can proceed against a copied core instead (option
  B from [architecture.md](architecture.md)) at the cost of duplication.
- Phases 3 and 4 can proceed in parallel with a stub on either side of the
  model/service boundary, if more than one person is working.
- Phase 5 is severable. A v4 client that does CRUD, query, and navigation but
  not `$apply` is already useful; ship 0–4 and follow with 5.
