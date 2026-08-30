#!/usr/bin/env python3
"""Fail the build when line coverage drops below the recorded baseline.

Phase 0 item 4 of docs/v4/plan/roadmap.md, enforcing the baseline stated in
docs/v4/plan/compatibility-contract.md: coverage on pyodata/v2/ may only go
up, never down. Without a gate that is a promise; with one it is a build
failure.

Usage:

    make coverage-floors          # runs the suite, then checks
    python3 tests/check_coverage_floors.py coverage.json

The floors are a ratchet. Raise one when real coverage rises comfortably past
it; never lower one to make a build pass -- a drop means tests were lost or
code was added untested, and that is the thing this file exists to catch.

Every measured file needs an entry. A new module without one fails the check
by design: it makes declaring a coverage floor part of adding a module, which
is what the phase 3 and 4 exit criteria require of pyodata/v4/.
"""

import json
import pathlib
import sys

# Floors are whole percent, set at or just below the measured value so that
# incidental churn in statement counts does not fail the build while a real
# regression does. Measured on the full suite (make test), Python 3.11 /
# lxml 6.x, at 383 passed:
#
#     pyodata/client.py      100.00      pyodata/v2/model.py     93.45
#     pyodata/exceptions.py  100.00      pyodata/v2/service.py   91.67
#     pyodata/vendor/SAP.py  100.00      TOTAL                   93.10
#
# Note that pyodata/client.py reaches 100% only under the full suite; the
# tests/integration/networking_libraries subset is what covers it.
FLOORS = {
    'pyodata/__init__.py': 100,
    'pyodata/client.py': 100,
    'pyodata/exceptions.py': 100,
    'pyodata/v2/__init__.py': 100,
    'pyodata/v2/model.py': 93,
    'pyodata/v2/service.py': 91,
    'pyodata/vendor/__init__.py': 100,
    'pyodata/vendor/SAP.py': 100,
}

TOTAL_FLOOR = 93


def check(report):
    """Compare a coverage JSON report against FLOORS; return a list of problems."""

    problems = []

    measured = {name.replace('\\', '/'): data['summary']['percent_covered']
                for name, data in report['files'].items()}

    for name, percent in sorted(measured.items()):
        if name not in FLOORS:
            problems.append(
                f'{name}: no coverage floor recorded. Add one to FLOORS in '
                f'{__file__} (measured {percent:.2f}%).')
        elif percent < FLOORS[name]:
            problems.append(
                f'{name}: {percent:.2f}% is below the recorded floor of {FLOORS[name]}%.')

    for name in sorted(FLOORS.keys() - measured.keys()):
        problems.append(
            f'{name}: has a coverage floor but was not measured. If the module '
            f'was removed, drop its floor in the same commit.')

    total = report['totals']['percent_covered']
    if total < TOTAL_FLOOR:
        problems.append(f'TOTAL: {total:.2f}% is below the recorded floor of {TOTAL_FLOOR}%.')

    return problems


def main(argv):
    """Check the coverage JSON named on the command line; 0 when it passes."""

    if len(argv) != 2:
        print(__doc__)
        return 2

    path = pathlib.Path(argv[1])
    if not path.exists():
        print(f'{path} not found; generate it with '
              f'"pytest --cov=pyodata --cov-report=json:{path}".', file=sys.stderr)
        return 2

    report = json.loads(path.read_text(encoding='utf-8'))
    problems = check(report)

    if problems:
        print('Coverage has regressed below the recorded baseline '
              '(docs/v4/plan/compatibility-contract.md):\n', file=sys.stderr)
        for problem in problems:
            print(f'  - {problem}', file=sys.stderr)
        print('\nThe floors are a ratchet: fix the coverage, do not lower the floor.\n'
              'If you are running a subset of the suite, run "make coverage-floors" '
              'instead -- some modules are only covered by the integration tests.',
              file=sys.stderr)
        return 1

    print(f'Coverage floors met (total {report["totals"]["percent_covered"]:.2f}%, '
          f'floor {TOTAL_FLOOR}%).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
