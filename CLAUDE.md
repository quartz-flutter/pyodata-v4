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
tests/               393 tests, pytest, ~93% line coverage on pyodata/
  fixtures/v4/       pinned OASIS ABNF corpus + annotation vocabularies
docs/usage/*.rst     user guide (sphinx)
docs/v4/             the v4 project: research, plan, fixtures  <- start here
```

`docs/v4/README.md` is the index for the v4 effort. Read it before touching
anything v4-related.

## Commands

```bash
python3 -m pip install -r dev-requirements.txt      # or, for the fast run only:
python3 -m pip install lxml pytest requests responses pytest-cov pyyaml

make test                       # pytest with coverage
python3 -m pytest tests -q --ignore=tests/integration    # fast unit run
python3 -m pytest tests -q --cov=pyodata --cov-report=term
make lint                       # pylint + flake8
make coverage-floors            # full suite + fail if coverage regressed
make check                      # lint + coverage-floors
make doc                        # sphinx into docs/_build/html
```

**Verified baseline (Python 3.11, lxml 6.x): 393 passed, 93% total coverage
under `make test`; 361 passed, 92% under the fast unit run.**
Record any deviation from this baseline; do not let it drift downward.
`make coverage-floors` enforces it — the per-module floors live in
`tests/check_coverage_floors.py` and are a ratchet: raise them, never lower
them. A new module with no floor recorded fails the check by design.

`tests/integration/networking_libraries/` needs `pytest-aiohttp`, `httpx` and
`respx`; it is excluded from the fast run above. Note that `pyodata/client.py`
reaches 100% coverage only when those tests run, so the floors are measured
against the full suite.

## The phase 0 gates

Three checks now guard every later change. If one fails, that is the finding —
do not adjust the gate to make it pass.

| Gate | File | What breaks it |
|---|---|---|
| G1 public API snapshot | `tests/test_public_api_snapshot.py` + `.json` | any public name, signature or member that moves, is renamed or disappears. Intentional additions: rerun with `--update` in the same commit |
| G2 v2 wire-format golden | `tests/test_wire_format_golden_v2.py` | any change to the bytes v2 puts on the wire — method, path, query string, headers, body, `$filter` rendering, Edm literals, batch framing |
| coverage floors | `tests/check_coverage_floors.py` | coverage falling below the recorded baseline, per module or in total |

One golden expectation is a pinned *known defect*, marked DEFECT in place and
due to change in phase 1: the `__range` lookup emitting `gte`/`lte`
(`service.py:1319`), which are not OData operators in any version. Updating
that expectation belongs in the same commit as the fix.

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

Work on a feature branch. Never commit directly to `master` — note the default
branch here is `master`, not `main`. Branch from an up-to-date `master`:

```bash
git fetch origin master
git checkout -b <branch> origin/master   # e.g. claude/phase-1-version-detection
git push -u origin <branch>              # same branch name on every push
```

If a task names a branch, use that name exactly; otherwise pick a short
descriptive one. The convention for agent-authored work here is
`claude/<topic>-<suffix>`.

- **Do not open a pull request unless asked.**
- One logical change per commit (`CONTRIBUTING.md`). No "fix previous commit"
  commits — amend or rebase instead. Messages explain *why*, not just what.
- Rule R4 of the compatibility contract is a git rule: a commit either
  relocates code with zero behaviour change, or it changes behaviour, never
  both. Phase 2's extraction into `pyodata/core/` is only reviewable if this
  holds.
- Do not rewrite history on a branch anyone else may have checked out — no
  force-push, rebase or amend once it is shared. On your own unshared branch it
  is fine.
- If a branch's pull request is already merged, that branch is finished. Do not
  stack follow-up commits on it; start a fresh branch from `master`.
- Run the gates before pushing, not after: `python3 -m pytest tests -q
  --ignore=tests/integration` at minimum, `make check` for anything touching
  `pyodata/`.

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
