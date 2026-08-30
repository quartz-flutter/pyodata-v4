# Prior art: what has already been tried

## Upstream SAP/python-pyodata

### Issue #39 "Add support for V4"

Opened 2019-07-22 by the project's founder (`filak-sap`), assigned to milestone
2.0.0, **still open in 2026**. The issue body is literally the text
`Place holder`. There is no design discussion, no accepted proposal, and no
merged implementation.

Related open issues: #217 ("Is Pyodata compatible with OData V4"), plus further
v4 enhancement requests filed in 2023 and 2024. The README and the sphinx docs
both still list exactly one supported feature: *"OData V2"*.

### The `wip-odata-v4` branch — a false lead

Upstream carries a branch named `wip-odata-v4`, last touched 2019-10-29.

**It contains no v4 code.** Inspecting its tree
(`git ls-tree -r --name-only origin/wip-odata-v4`) shows the ordinary
`pyodata/{__init__,client,exceptions}.py`, `pyodata/v2/{model,service}.py`,
`pyodata/vendor/SAP.py` — and nothing else. There is no `pyodata/v4/` directory.
The branch is an old snapshot of `master` from around v1.3.0 whose name
describes an intention that was never acted on.

Anyone planning this work will find that branch first and lose time on it.
It is a dead end; do not clone it expecting a starting point.

### The `experimental_v3` branch — the anti-pattern, from the author himself

Far more instructive. Three commits on top of the same 2019 base:

| Commit | Message |
|---|---|
| `5ceafac` | `HACK HACK HACK: experimental V3` |
| `a545948` | `service: do not read response.d if not exists` — *"Eh, that's a stupid approach but I have no time to think."* |
| `726d949` | `model: drop the 7th microseconds digit` |

The technique was to make the **v2 code path tolerant** of a newer protocol:

```python
-            entities = content['d']['results']
+            try:
+                entities = content['d']['results']
+            except KeyError:
+                entities = content['value']
```

repeated at five call sites, plus gutting `EdmDateTimeTypTraits.from_json` so
that `/Date(ms)/` parsing was replaced wholesale by ISO parsing:

```python
     def from_json(self, value):
-        matches = re.match(r"^/Date\((.*)\)/$", value)
-        ...
+        return self.from_literal(value)
```

Total diff: 35 lines across two files.

**Why this fails our brief.** Every one of those changes is a *deterioration of
v2*, which is precisely what this fork must not do:

1. `except KeyError` cannot distinguish "this is a v4 payload" from "the v2
   server returned a malformed body". A genuine v2 protocol error is silently
   reinterpreted as v4 and produces a wrong result instead of an exception.
2. Deleting the `/Date(ms)/` parser removes working, tested v2 behaviour to make
   room for v4. Both are needed; neither can be the other's default.
3. `value is 'null'` (in `5ceafac`) is an identity comparison against a string
   literal — a latent bug that only happens to work under CPython interning.
4. The dispatch is scattered across the call sites of the deepest layer, so
   there is no single place that knows which protocol is in play, and no way to
   test either protocol in isolation.

The author's own commit message is the honest verdict. **Neither branch was ever
merged.** This fork starts from a clean sheet with one firm rule taken from that
experience: *version dispatch happens once, at the top.*

## The wider Python ecosystem

| Project | v4? | Relevance |
|---|---|---|
| [`SAP/python-pyodata`](https://github.com/SAP/python-pyodata) | no | this fork's upstream; mature v2, strong SAP annotation support, good error-policy design |
| [`tuomur/python-odata`](https://github.com/tuomur/python-odata) | yes | the most usable v4 client in Python. ORM/declarative style — you subclass an entity base rather than reflecting metadata into proxies. Useful reference for v4 URL and payload handling; **the API philosophy is different from pyodata's and should not be copied** |
| [`OData/odatapy-client`](https://github.com/OData/odatapy-client) | partial | official-ish, targets v4.0, explicitly incomplete ("serves only parts of client and client-side proxy generation") |
| `Odata-py`, `odata-query` | n/a | `odata-query` builds `$filter` ASTs and targets SQLAlchemy; the filter-grammar handling is worth reading when implementing v4 lambda operators |

**Conclusion.** There is no drop-in v4 implementation to adopt, and no upstream
branch to resume. The valuable prior art is negative: it tells us which approach
to rule out. See [`../plan/architecture.md`](../plan/architecture.md).

## Reproducing these findings

```bash
git clone https://github.com/SAP/python-pyodata /tmp/upstream
cd /tmp/upstream
git fetch --depth 50 origin 'refs/heads/*:refs/remotes/origin/*'
git ls-tree -r --name-only origin/wip-odata-v4 | grep -v '^tests/'   # no pyodata/v4/
git show 5ceafac a545948 726d949                                     # the V3 hack
```
