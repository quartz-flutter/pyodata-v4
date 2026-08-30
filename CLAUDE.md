# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repository is

`pyodata-v4` is a fork of [SAP/python-pyodata](https://github.com/SAP/python-pyodata),
an enterprise-grade Python OData **v2** client. The fork exists to **add OData v4
support without degrading the existing v2 implementation**.

The package name on disk is `pyodata`. The fork tracks upstream `master`
(currently at v1.12.0) and carries a small number of local commits.

## The prime directive of this fork

> Add OData v4 compatibility **without losing relevant functionality, quality, or
> causing general deterioration** of the v2 implementation.

This is not a rewrite and it is not a "make v2 tolerant of v4 payloads" patch.
Upstream already tried the latter on the `experimental_v3` branch and the author
labelled his own commit *"Eh, that's a stupid approach but I have no time to
think."* — see `docs/v4/research/prior-art.md`. Do not repeat it.

Concretely, three rules bind every change:

1. **v2 behaviour is frozen.** No change may alter what the v2 code path sends on
   the wire or returns to the caller, except to fix a defect that is documented
   as a defect. `try: ... except KeyError: <v4 fallback>` inside v2 code is
   forbidden — it silently converts v2 protocol errors into v4 guesses.
2. **Version dispatch happens once, at the top.** `pyodata.Client` selects a
   dialect; below that point code knows which protocol it speaks. Nothing deep in
   the stack sniffs payload shape to decide.
3. **Every refactor is behaviour-preserving and proven so.** The full test suite
   must pass unchanged before and after. Moves and behaviour changes never share
   a commit.

See `docs/v4/plan/compatibility-contract.md` for the full contract and its
enforcement gates.

## Layout

```
pyodata/
  __init__.py        exports Client
  client.py          Client.__new__ / build_async_client — version dispatch lives here
  exceptions.py      PyODataException hierarchy (shared, version-agnostic)
  v2/model.py        ~2.8k lines. CSDL 1.0/2.0 XML parser -> Schema object graph
  v2/service.py      ~2.0k lines. Request builders, proxies, JSON decoding, batch
  vendor/SAP.py      SAP BTP auth helper + SAP error-header response hook
tests/               263 tests, pytest, ~91% line coverage on pyodata/
docs/usage/*.rst     user guide (sphinx)
docs/v4/             the v4 project: research, plan, fixtures  <- start here
```

`docs/v4/README.md` is the index for the v4 effort. Read it before touching
anything v4-related.

## Commands

```bash
# deps (note: pylint==2.8.3 in dev-requirements.txt does NOT build on Python >=3.11)
python3 -m pip install lxml pytest requests responses pytest-cov

make test                       # pytest with coverage
python3 -m pytest tests -q --ignore=tests/integration    # fast unit run
python3 -m pytest tests -q --cov=pyodata --cov-report=term
make lint                       # pylint + flake8 (see caveat above)
make check                      # lint + test
make doc                        # sphinx into docs/_build/html
```

**Verified baseline (Python 3.11, lxml 6.x): 263 passed, 91% total coverage.**
Record any deviation from this baseline; do not let it drift downward.

`tests/integration/networking_libraries/` needs `pytest-aiohttp`, `httpx` and
`respx`; it is excluded from the fast run above.

## Conventions

- Python >= 3.10. `lxml` is the only runtime dependency — keep it that way.
- f-strings preferred; the codebase still contains legacy `.format()` calls, do
  not mass-convert them.
- `.flake8` ignores E501; `.pylintrc` is permissive at module level via
  `# pylint: disable=` headers in `v2/model.py` and `v2/service.py`. Prefer
  narrow, local disables in new code over widening those headers.
- Note the deliberate spelling `proprty` / `proprties` throughout the model layer.
  It is public API. Do not "fix" it.
- Parser robustness is configurable, not hard-coded: `Config` +
  `ErrorPolicy` (`PolicyFatal` / `PolicyWarning` / `PolicyIgnore`) per
  `ParserError` category. New parse failures must route through
  `config.err_policy(...).resolve(ex)` and set `schema._is_valid = False`, not
  raise unconditionally.
- REUSE licensing: `.reuse/dep5` has `Files: *` -> Apache-2.0, so new files need
  no per-file header.
- Contributing style (inherited from upstream): one logical change per commit, no
  "fix previous commit" commits (amend/rebase instead), every PR carries a test
  or a justification for its absence.

## Git

Work on `claude/odata-v4-compatibility-50ejxo`. Push with
`git push -u origin claude/odata-v4-compatibility-50ejxo`. Do not open a pull
request unless asked.

## Traps found the hard way

- `MetadataBuilder.EDMX_WHITELIST` / `EDM_WHITELIST` already contain the **v4**
  namespaces (`http://docs.oasis-open.org/odata/ns/edmx` and `.../ns/edm`). A v4
  metadata document therefore gets *past* the namespace gate and fails later with
  confusing errors, or — worse — parses into a silently wrong schema. See
  `docs/v4/research/parser-behaviour-v4-input.md` for the exact failure modes.
- `Types.Types` is process-global mutable state, and
  `MetadataBuilder.update_global_variables_with_alias` mutates module-level
  globals (`SAP_ANNOTATION_VALUE_LIST`, `SAP_VALUE_HELPER_DIRECTIONS`). Two
  services parsed in one process share it. v4 must not add a second writer to
  that state; give v4 its own registry.
- `Service.config` is a plain dict (`{'http': {'update_method': 'PATCH'}}`),
  unrelated to `model.Config`. Two different things named "config".
- `HttpError.__new__` dispatches on the class attribute `HttpError.VendorType` —
  another process-global. `pyodata.vendor.SAP` sets it.
