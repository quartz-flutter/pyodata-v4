# The compatibility contract

"Without deterioration" only means something if it is checkable. This document
turns the brief into rules with gates behind them.

## The baseline

Measured on this branch at commit `c8258ee`, Python 3.11.15, lxml 6.x:

```
263 passed
                             Stmts   Miss  Cover
pyodata/client.py               57     42    26%
pyodata/exceptions.py           14      0   100%
pyodata/v2/model.py           1787    118    93%
pyodata/v2/service.py         1009    101    90%
pyodata/vendor/SAP.py           45      0   100%
TOTAL                         2914    261    91%
```

Reproduce:

```bash
python3 -m pip install lxml pytest requests responses pytest-cov
python3 -m pytest tests -q --ignore=tests/integration --cov=pyodata --cov-report=term
```

Every phase re-states these numbers. Test count may only go **up**; coverage on
`pyodata/v2/` may only go **up**.

### After phase 0

Measured at commit `3ef1ea1`, same interpreter and lxml. Phase 0 changed no
`pyodata/` source, so the movement is entirely new tests exercising existing
code:

```
396 passed          (make test, the full suite)
                             Stmts   Miss  Cover
pyodata/client.py               57      0  100%
pyodata/exceptions.py           14      0  100%
pyodata/v2/model.py           1787    117   93%
pyodata/v2/service.py         1009     84   92%
pyodata/vendor/SAP.py           45      0  100%
TOTAL                         2914    201   93%
```

The fast unit run (`--ignore=tests/integration`) gives 364 passed at 92%;
`pyodata/client.py` is covered only by the integration tests, which is why the
floors below are measured against the full suite. These numbers are now
enforced rather than recorded — see G5.

## The five rules

### R1 — v2 wire behaviour is frozen

No change may alter the HTTP method, path, query string, headers, or body that
the v2 code path produces, nor the Python objects it returns, **except** to fix
a defect that is documented as a defect in
[../research/parser-behaviour-v4-input.md](../research/parser-behaviour-v4-input.md)
or a successor list, and then only in a commit that does nothing else.

*Gate:* golden/characterization tests (see G2).

### R2 — no protocol sniffing below the dispatch point

`pyodata.Client` decides the version. Below it, no code inspects a payload,
header, or namespace to infer which protocol it is speaking.

Specifically banned in `pyodata/v2/`:

```python
try:
    x = body['d']
except KeyError:
    x = body['value']     # <- forbidden
```

*Gate:* a lint/grep check in CI for `except KeyError` immediately followed by a
v4-shaped fallback in v2 modules, plus code review.

### R3 — public API addresses never move

Every name importable from `pyodata`, `pyodata.client`, `pyodata.exceptions`,
`pyodata.v2.model`, `pyodata.v2.service`, `pyodata.vendor.SAP` today must remain
importable from the same module afterwards. Extraction relocates definitions and
re-exports them; it never relocates import paths.

This includes the odd spellings (`proprty`, `proprties`, `ExternalAnnontation`,
`EdmStructTypTraits`) and the deprecated shims (`Edmx`, the `namespaces=`
kwarg). They are API.

*Gate:* the API snapshot test (G1).

### R4 — moves and behaviour changes never share a commit

A commit either relocates code with zero semantic change, or it changes
behaviour. Never both. A reviewer must be able to verify a move by reading the
diff, not by reasoning about it.

*Gate:* review; commits titled `refactor:` must show a green suite and no test
diff.

### R5 — v4 gets its own state

v4 must not add entries to `Types.Types`, `SAP_ANNOTATION_VALUE_LIST`, or
`SAP_VALUE_HELPER_DIRECTIONS`. These are process-global and already leak between
parses; a second writer would make that a cross-version bug. v4 owns its
registries.

*Gate:* a test that parses a v4 document and then asserts the v2 `Types` registry
and the SAP globals are byte-identical to their pre-parse state.

## The gates

### G1 — public API snapshot

A test that enumerates the public names (and, for classes, their public
attributes and method signatures) of every current module and compares them
against a checked-in snapshot file. Any addition requires updating the snapshot
in the same commit — which makes an accidental removal or rename impossible to
merge silently.

```
tests/test_public_api_snapshot.py
tests/public_api_snapshot.json
```

**Built in phase 0, before any refactoring** — 157 module-level names pinned,
including the historic spellings and the deprecated shims. Regenerate after an
intentional addition with
`python3 tests/test_public_api_snapshot.py --update`, in the same commit.

### G2 — v2 wire-format golden tests

The existing 263 tests assert a lot, but they assert *outcomes*, not always the
exact bytes. Before extraction, add characterization tests that pin, for a
representative set of operations against `tests/metadata.xml`:

- `get_method()`, `get_path()`, `get_query_params()`, `get_body()`,
  `get_headers()` for every request class
- the exact `$filter` string produced by each lookup in the DSL
- the exact literal produced by `to_literal` for every registered `Edm.*` type,
  including `null_value`
- `EntityKey.to_key_string()` for single and composite keys
- the multipart batch/changeset body, byte for byte

These are cheap to write (the getters are already public — `docs/usage/urls.rst`
documents them as a feature) and they are what makes R1 enforceable rather than
aspirational.

**Built in phase 0**: `tests/test_wire_format_golden_v2.py`, 87 tests. Verified
as a tripwire by mutation — reversing the `substringof` argument order,
dropping the `X-Requested-With` header, dropping `Edm.Int64`'s `L` suffix, and
removing the blank line the SAP gateway needs for an empty batch part each fail
it; the last two pass the pre-existing 224 model and service tests silently,
which is the case for the gate in one line.

### G3 — cross-version isolation tests

Parse a v2 document and a v4 document in the same process, in both orders, and
assert both schemas are correct. This catches R5 violations and any shared
mutable state introduced later.

### G4 — CI matrix unchanged

`python-tests-compatibility.yml` runs Python 3.10–3.14 × lxml 4.6.5–6.1.1. v4
code must pass the same matrix. No new runtime dependency beyond `lxml`.

*Known CI defect, fixed in phase 0:* `dev-requirements.txt` pinned
`pylint==2.8.3`, which pulls a `wrapt` that fails to build on Python ≥3.11, so
`make lint` and `make check` could not run locally on a modern interpreter. Now
`pylint>=3.3` / `flake8>=7.0`, with the options modern pylint removed dropped
from `.pylintrc` and its newer modernization checks disabled — the v2 code they
flag is frozen by R1 and must not be rewritten for lint's sake.

### G5 — coverage floors

`tests/check_coverage_floors.py`, run by `make coverage-floors` and by CI in
place of the bare `make test`, fails the build when any module or the total
drops below the recorded baseline above. A module with no floor recorded is
itself a failure, which makes declaring one part of adding a module — as the
phase 3 and 4 exit criteria require of `pyodata/v4/`.

The floors are a ratchet: raise them when coverage rises comfortably past
them, never lower them to make a build pass.

## What "no loss of relevant functionality" covers

Not just tests passing. The following v2 capabilities are load-bearing for real
users and must still work, and be seen to work, at the end:

| Capability | Where |
|---|---|
| Configurable parser error policies per element category | `Config` / `ErrorPolicy` / `ParserError` |
| Permissive parsing of broken enterprise metadata (`NullType`, `is_valid`) | `Schema.from_etree` |
| SAP annotations: labels, creatable/updatable/sortable/filterable, value helps | `StructTypeProperty`, `ValueHelper` |
| SAP BTP token auth and `sap-message` error headers | `pyodata/vendor/SAP.py` |
| Batch and changesets | `create_batch`, `create_changeset` |
| Async execution (`async_execute`, `build_async_client`) | `ODataHttpRequest` |
| `response_hook` for raw-response inspection | `ODataHttpRequest._call_handler` |
| URL-only usage (no HTTP), e.g. the Locust integration | `docs/usage/urls.rst` |
| `retain_null` semantics | `Config.retain_null`, `EntityProxy.__init__` |
| Static metadata (no `$metadata` round-trip) | `Client(metadata=...)` |
| Cross-origin `__next` rejection | `ODataHttpRequest._build_request` |
| Namespace whitelists incl. legacy Microsoft EDM versions | `MetadataBuilder` |

Each of these needs a v4 answer too — tracked in
[conformance-matrix.md](conformance-matrix.md).

## Definition of done for the whole project

1. Baseline suite still passes; v2 coverage ≥ 93% / 90% per module; API snapshot
   unchanged apart from additions.
2. v4 unit suite covers CSDL 4.0 parsing, URL construction, JSON decoding,
   actions/functions, and batch, at ≥ 90% line coverage on `pyodata/v4/`.
3. Opt-in integration tests pass against TripPin (v4) **and** Northwind V2 (v2).
4. `README.md`, `docs/index.rst` and the user guide state both versions, with a
   v2/v4 differences page.
5. `CHANGELOG.md` documents the v4 addition and states plainly that v2 behaviour
   is unchanged.
6. Cross-version isolation test (G3) passes in both orders.
