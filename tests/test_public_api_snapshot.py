"""Gate G1 of the OData v4 compatibility contract: the public API snapshot.

Rule R3 (docs/v4/plan/compatibility-contract.md): every name importable from
the modules below today must remain importable from the same module. This test
enumerates the public names of each module -- and, for classes and functions
defined inside pyodata, their public members and signatures -- and compares
the result against the checked-in ``tests/public_api_snapshot.json``.

Any intentional API addition must update the snapshot in the same commit:

    python3 tests/test_public_api_snapshot.py --update

An accidental removal, rename, or signature change fails this test and can
therefore never merge silently. This includes the historic spellings
(``proprty``, ``ExternalAnnontation``, ...) and the deprecated shims
(``Edmx``, ...) -- they are API.
"""

import importlib
import inspect
import json
import pathlib
import sys

import pytest

SNAPSHOT_FILE = pathlib.Path(__file__).parent / 'public_api_snapshot.json'

MODULES = [
    'pyodata',
    'pyodata.client',
    'pyodata.exceptions',
    'pyodata.v2',
    'pyodata.v2.model',
    'pyodata.v2.service',
    'pyodata.vendor',
    'pyodata.vendor.SAP',
]


def _signature_of(obj):
    """Best-effort signature string; None where introspection fails."""

    try:
        return str(inspect.signature(obj))
    except (ValueError, TypeError):
        return None


def _describe_class(cls):
    """Public shape of a class: its own public members, by kind.

    Only the class's own ``__dict__`` is walked (inherited members are pinned
    on the class that defines them), so the description stays stable across
    Python versions. Values are never recorded -- some class attributes are
    process-global mutable state (``Types.Types``, ``HttpError.VendorType``).
    """

    members = {}
    for name in sorted(vars(cls)):
        if name.startswith('_'):
            continue
        raw = inspect.getattr_static(cls, name)
        if isinstance(raw, staticmethod):
            members[name] = 'staticmethod' + (_signature_of(getattr(cls, name)) or '(?)')
        elif isinstance(raw, classmethod):
            members[name] = 'classmethod' + (_signature_of(getattr(cls, name)) or '(?)')
        elif isinstance(raw, property):
            members[name] = 'property'
        elif inspect.isfunction(raw):
            members[name] = 'method' + (_signature_of(raw) or '(?)')
        elif inspect.isclass(raw):
            members[name] = 'class'
        else:
            members[name] = 'attribute'
    init = getattr(cls, '__init__', None)
    description = {'members': members}
    # Only a constructor pyodata itself defines is pyodata's API. An inherited
    # stdlib __init__ (Enum, Exception, ...) is an implementation detail whose
    # signature -- and even whose presence here -- varies by Python version:
    # enum.Enum.__init__ is a Python function on 3.11+ but a C
    # wrapper_descriptor on 3.10, so recording it would fail the snapshot on
    # half the supported matrix.
    defined_here = (getattr(init, '__module__', None) or '').startswith('pyodata')
    if init is not None and inspect.isfunction(init) and defined_here:
        description['init'] = _signature_of(init) or '(?)'
    return description


def describe_module(module_name):
    """Public shape of one module: every non-underscore name, by kind."""

    module = importlib.import_module(module_name)
    names = {}
    for name in sorted(vars(module)):
        if name.startswith('_'):
            continue
        value = vars(module)[name]
        if inspect.ismodule(value):
            names[name] = 'module'
        elif inspect.isclass(value):
            if (value.__module__ or '').startswith('pyodata'):
                names[name] = _describe_class(value)
            else:
                names[name] = 'class (external)'
        elif inspect.isfunction(value):
            if (value.__module__ or '').startswith('pyodata'):
                names[name] = 'function' + (_signature_of(value) or '(?)')
            else:
                # signatures of foreign functions can embed unstable reprs
                # (default values like "<function quote_plus at 0x...>")
                names[name] = 'function (external)'
        elif callable(value):
            names[name] = 'callable'
        else:
            names[name] = 'attribute'
    return names


def build_snapshot():
    # import everything first: importing a submodule binds it as an attribute
    # of its parent package, so the visible names of a module depend on what
    # has been imported, not just on its source. Importing the whole list up
    # front makes the result independent of import order elsewhere.
    for module_name in MODULES:
        importlib.import_module(module_name)
    return {module_name: describe_module(module_name) for module_name in MODULES}


def _flatten(prefix, node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            _flatten(f'{prefix}.{key}' if prefix else key, value, out)
    else:
        out[prefix] = node


def test_public_api_snapshot():
    assert SNAPSHOT_FILE.exists(), (
        f'{SNAPSHOT_FILE} is missing; generate it with '
        f'"python3 {pathlib.Path(__file__).relative_to(pathlib.Path.cwd())} --update"'
    )

    expected = json.loads(SNAPSHOT_FILE.read_text(encoding='utf-8'))
    actual = build_snapshot()

    if actual == expected:
        return

    flat_expected, flat_actual = {}, {}
    _flatten('', expected, flat_expected)
    _flatten('', actual, flat_actual)

    problems = []
    for key in sorted(flat_expected.keys() - flat_actual.keys()):
        problems.append(f'REMOVED:  {key} (was: {flat_expected[key]})')
    for key in sorted(flat_actual.keys() - flat_expected.keys()):
        problems.append(f'ADDED:    {key} (is: {flat_actual[key]})')
    for key in sorted(flat_expected.keys() & flat_actual.keys()):
        if flat_expected[key] != flat_actual[key]:
            problems.append(f'CHANGED:  {key}\n  snapshot: {flat_expected[key]}\n  current:  {flat_actual[key]}')

    pytest.fail(
        'Public API differs from tests/public_api_snapshot.json.\n'
        'Removals and renames violate rule R3 of the compatibility contract\n'
        '(docs/v4/plan/compatibility-contract.md). For intentional additions,\n'
        'regenerate the snapshot in the same commit:\n'
        '    python3 tests/test_public_api_snapshot.py --update\n\n' + '\n'.join(problems)
    )


def main():
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    if '--update' not in sys.argv:
        print(__doc__)
        print('Run with --update to (re)generate the snapshot file.')
        return 1
    SNAPSHOT_FILE.write_text(
        json.dumps(build_snapshot(), indent=1, sort_keys=True) + '\n',
        encoding='utf-8')
    print(f'Wrote {SNAPSHOT_FILE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
