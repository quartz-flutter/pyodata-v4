# Architecture decision: how v4 gets added

**Status:** proposed · **Date:** 2026-08-30 · **Supersedes:** nothing

## The question

The brief is "add OData v4 compatibility without losing relevant functionality,
quality, or general deterioration". Three structurally different ways to do that.

## Options considered

### A. Make the v2 code path tolerant of v4

Add v4 branches inside `pyodata/v2/`: `try: content['d'] except KeyError:
content['value']`, accept both literal forms, widen the parsers.

**Rejected.** This is verbatim what upstream's `experimental_v3` branch did, and
its author's own commit message reads *"Eh, that's a stupid approach but I have
no time to think"* — see [../research/prior-art.md](../research/prior-art.md).
It fails the brief on its own terms:

- `except KeyError` cannot tell a v4 payload from a malformed v2 one. Real v2
  protocol errors become silent wrong answers. That *is* deterioration.
- It cannot express the structural differences at all. v4 has no `Association`,
  so `EntityProxy.nav()` — which resolves through `AssociationSet` — has nothing
  to widen. Tolerance handles formatting; navigation, operations and inheritance
  are not formatting.
- Every conditional doubles the state space of the most heavily-tested code in
  the library. Coverage stays at 91% while meaning half as much.

### B. Copy `pyodata/v2/` to `pyodata/v4/` and edit

**Rejected, but respect its one real virtue:** it carries *zero* risk to v2.

Against: ~4800 duplicated lines. Every future fix — a datetime edge case, a
`$filter` escaping bug, a transport change — has to be found and applied twice,
and in practice will not be. The two copies drift, and the v4 copy inherits
today's v2 bugs (the `gte`/`lte` typo, the strict enum range check) frozen in
amber. Over a year this is a larger quality loss than option A, just deferred.

### C. Shared core + version dialects  ← **chosen**

Extract the genuinely version-agnostic machinery into `pyodata/core/`, keep
`pyodata/v2/` as the v2 dialect (public API byte-identical to today), and add
`pyodata/v4/` as a sibling dialect. Dispatch once, in `pyodata.Client`.

The audit ([../research/codebase-audit.md](../research/codebase-audit.md))
measured how much is actually shared: **~19% genuinely shared, ~50% same-concept-
different-rendering, ~17% v2-only, ~14% vendor.** That 19% is small enough to
extract safely and large enough to be worth it — it is also, not coincidentally,
the highest-value code: `ODataHttpRequest`'s deferred-execution and async
machinery, `ODataHttpResponse`, `Config`/`ErrorPolicy`, `Identifier`,
`TypTraits`, `VariableDeclaration`, `ListWithTotalCount`.

The 50% "dialect" band is deliberately **not** unified into one parameterised
implementation. That way lies option A's conditional soup. Each dialect gets its
own concrete classes; they share base classes and helpers, not branches.

## Target layout

```
pyodata/
  __init__.py            Client
  client.py              version detection + dispatch  (the ONLY place that branches on version)
  exceptions.py          unchanged, shared
  core/
    __init__.py
    config.py            Config, ErrorPolicy, PolicyFatal/Warning/Ignore, ParserError
    identifier.py        Identifier, TypeInfo, IdentifierInfo
    typ.py               Typ, Collection, TypTraits, VariableDeclaration, EdmStructTypeSerializer
    http.py              ODataHttpRequest, ODataHttpResponse, urljoin, ListWithTotalCount
    lookups.py           the __contains/__in/__range lookup DSL (rendering delegated to the dialect)
  v2/
    __init__.py
    model.py             v2 CSDL parser + v2 traits + Association/AssociationSet   (public API unchanged)
    service.py           v2 requests, proxies, JSON-verbose decoding, multipart batch
  v4/
    __init__.py
    model.py             CSDL 4.0/4.01 XML parser: NavigationProperty, Action/Function, Singleton, TypeDefinition, BaseType, vocabulary annotations
    service.py           v4 URLs, v4 JSON decoding, actions/functions, JSON batch
    traits.py            v4 Edm literal forms (no prefixes, no suffixes) + Edm.Date/TimeOfDay/Duration
  vendor/
    SAP.py               unchanged, version-agnostic
```

### Compatibility shims are mandatory

`pyodata/v2/model.py` and `pyodata/v2/service.py` must keep re-exporting every
name they export today, from their current import path, with unchanged
behaviour. Users import `from pyodata.v2.model import Config, PolicyWarning`
and `from pyodata.v2.service import GetEntitySetFilter` today; those must keep
working forever. Extraction moves the *definition*, never the *address*.

An automated public-API snapshot test enforces this — see
[compatibility-contract.md](compatibility-contract.md).

## Version detection and dispatch

`Client` currently takes `odata_version=2`. After this work:

```python
pyodata.Client(url, session)                  # auto-detect (new default)
pyodata.Client(url, session, odata_version=2) # force v2 — behaves exactly as today
pyodata.Client(url, session, odata_version=4) # force v4
```

Detection order, on the fetched `$metadata` document:

1. `edmx:Edmx/@Version` — `4.0` / `4.01` -> v4; `1.0` -> v2/v3.
2. Failing that, the EDMX namespace URI: `docs.oasis-open.org/odata/ns/edmx`
   -> v4; `schemas.microsoft.com/ado/2007/06/edmx` -> v2.
3. Failing that, the `OData-Version` response header on the `$metadata` fetch.
4. Otherwise raise `PyODataException` naming what was found. **Never guess.**

An explicit `odata_version` **skips detection entirely** — `odata_version=2`
must take the identical code path it takes today, so that no existing user's
behaviour can change as a side effect of adding detection.

Independently and immediately: when a v4 document reaches the *v2* parser, it
must fail with a clear message ("this looks like OData 4.0 metadata; pass
`odata_version=4`") instead of today's
`Type None is not valid as underlying type for EnumType`. That is a v2 usability
fix worth shipping in phase 1 regardless of how far the v4 work gets.

## API shape for v4

Keep pyodata's idiom. A v4 user should recognise the library:

```python
svc = pyodata.Client(URL, requests.Session())        # detects v4

svc.entity_sets.People.get_entities().top(5).execute()
svc.entity_sets.People.get_entity('russellwhyte').execute()
svc.entity_sets.People.get_entities().filter(Name__contains='ell').execute()
```

The lookup DSL (`__contains`, `__startswith`, `__in`, `__range`, `__gt`, ...) is
genuinely good and version-agnostic *as an interface*. It stays identical; only
its rendering differs — `contains(Name,'ell')` in v4 where v2 emits
`substringof('ell',Name) eq true`.

v4-only surface, added as new names rather than by overloading v2 ones:

```python
svc.singletons.Me.get_entity().execute()             # Singleton
svc.functions.GetNearestAirport(lat=33).execute()    # unbound function, GET
svc.actions.ResetDataSource().execute()              # unbound action, POST
person.action('Trippin.ShareTrip').set(tripId=1).execute()   # bound action
q.expand('Trips($select=Name;$top=5)')               # nested expand
q.search('boise').apply('groupby((City),aggregate($count as N))')
```

## Consequences

**Good**

- v2 risk is bounded to a mechanical, test-guarded extraction of ~900 lines,
  none of which changes behaviour.
- Bug fixes in transport, config, and type plumbing land once.
- Each dialect is independently testable and independently readable. A reader of
  `v4/service.py` is never asked to hold v2 in their head.
- The v4 dialect can adopt v4-native idioms (actions, singletons, `$apply`,
  vocabulary annotations) without contorting a v2-shaped object graph.

**Costs, accepted**

- Real refactoring work in phase 1 before any v4 feature exists. Mitigated by
  doing it as pure moves with re-export shims, one module per commit, full suite
  green at every step.
- `pyodata/core/` becomes a de-facto public API that must be kept stable. It
  will be documented as provisional (`pyodata.core` is internal until 2.0).
- Two dialects to maintain. This is inherent to supporting two protocols
  honestly, and is the cost the brief is asking us to pay rather than avoid.

**Explicitly out of scope for v1 of this work**

CSDL JSON metadata (4.01), `Edm.Geography*`/`Edm.Geometry*`, delta responses,
async request processing (`Prefer: respond-async`), and v3. Recorded in
[conformance-matrix.md](conformance-matrix.md) as deferred, not forgotten.
