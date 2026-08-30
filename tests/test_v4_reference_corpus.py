"""The vendored v4 reference material is present, intact, and readable.

Phase 0 item 5 of docs/v4/plan/roadmap.md, whose exit criterion is that "the
ABNF corpus is in the tree and readable by the test suite". These tests are
that criterion, and they double as a guard on the vendoring itself: the files
are pinned third-party artefacts (tests/fixtures/v4/PROVENANCE.md) and must
never be edited in place, so a change in their shape means a bad re-pin or a
local edit, either of which should fail loudly here rather than quietly skew a
phase 4 conformance run.

Nothing here tests pyodata; there is no v4 code yet. Phase 4 parametrizes the
real literal and URL tests over the same corpus.
"""

import collections
import pathlib

import pytest
from lxml import etree

from tests.conftest import contents_of_fixtures_file, load_abnf_testcases

FIXTURES_V4 = pathlib.Path(__file__).parent / 'fixtures' / 'v4'
EDM_V4_NAMESPACE = 'http://docs.oasis-open.org/odata/ns/edm'

# Namespace each vendored vocabulary must declare, keyed by file name. Phase 3
# item 8 maps these onto the v2 sap:* annotation surface.
VOCABULARIES = {
    'Org.OData.Core.V1.xml': 'Org.OData.Core.V1',
    'Org.OData.Capabilities.V1.xml': 'Org.OData.Capabilities.V1',
    'Org.OData.Measures.V1.xml': 'Org.OData.Measures.V1',
    'Org.OData.Validation.V1.xml': 'Org.OData.Validation.V1',
    'Org.OData.Aggregation.V1.xml': 'Org.OData.Aggregation.V1',
    'com.sap.vocabularies.Common.v1.xml': 'com.sap.vocabularies.Common.v1',
    'com.sap.vocabularies.UI.v1.xml': 'com.sap.vocabularies.UI.v1',
}


def test_abnf_construction_rules_present():
    """The full 4.01/4.0 URL and literal grammar is in the tree."""

    grammar = contents_of_fixtures_file('fixtures/v4/abnf/odata-abnf-construction-rules.txt').decode('utf-8')

    assert len(grammar.splitlines()) == 1298
    # a few rules phase 4 builds directly on
    for rule in ['odataUri', 'keyPredicate', 'primitiveLiteral', 'binaryValue', 'guidValue']:
        assert f'{rule} ' in grammar, f'{rule} missing from the construction rules'


def test_abnf_testcases_are_readable():
    """The corpus loads, and its shape is what PROVENANCE.md records."""

    testcases = load_abnf_testcases()

    assert len(testcases) == 840
    assert len([case for case in testcases if 'FailAt' in case]) == 79
    assert len({case['Rule'] for case in testcases}) == 83
    assert all('Rule' in case for case in testcases)


def test_abnf_testcases_survive_yaml_quirks():
    """The two upstream quirks reach the caller intact rather than mangled.

    Both would otherwise be silently normalised into something that no longer
    tests what the vector was written to test. See PROVENANCE.md.
    """

    testcases = load_abnf_testcases()
    inputs = [case.get('Input') for case in testcases]

    # the deliberate raw tab: "a tab separates $orderby=Name<TAB>asc"
    assert '$orderby=Name\tasc' in inputs

    # Edm.Date literals YAML would turn into (invalid) Python dates
    assert '0000-01-01' in inputs
    assert all(isinstance(value, str) for value in inputs if value is not None)


def test_abnf_testcases_reject_the_v2_binary_literal():
    """X'1a2B3c4D' is a negative vector: the v2 binary form v4 must reject.

    This client emits it today via EdmBinaryTypTraits('(?:binary|X)'). It is
    the concrete reason the v4 traits need their own registry rather than
    extending Types.Types (compatibility contract rule R5).
    """

    testcases = load_abnf_testcases()
    vectors = [case for case in testcases if case.get('Input') == "X'1a2B3c4D'"]

    assert len(vectors) == 1
    assert vectors[0]['Rule'] == 'binaryLiteral'
    assert vectors[0]['FailAt'] == 0


def test_abnf_testcases_cover_the_literal_rules_phase_four_needs():
    """Every rule phase 4 leans on has vectors, so the corpus can drive it."""

    counts = collections.Counter(case['Rule'] for case in load_abnf_testcases())

    for rule in ['odataUri', 'binaryLiteral', 'orderby', 'primitiveLiteral', 'filter', 'expand', 'select']:
        assert counts[rule] > 0, f'no vectors for {rule}'


@pytest.mark.parametrize('file_name,namespace', sorted(VOCABULARIES.items()))
def test_vocabulary_parses_as_csdl_4(file_name, namespace):
    """Each vendored vocabulary is well-formed CSDL 4.0 declaring its namespace.

    Parsed with lxml only -- the runtime dependency rule (contract G4) holds
    for the fixtures too.
    """

    root = etree.fromstring(contents_of_fixtures_file(f'fixtures/v4/vocabularies/{file_name}'))
    schemas = root.iter(f'{{{EDM_V4_NAMESPACE}}}Schema')
    namespaces = [schema.get('Namespace') for schema in schemas]

    assert namespaces == [namespace]


def test_vendored_files_are_documented():
    """Every vendored file appears in PROVENANCE.md, with nothing undocumented.

    Vendored material without recorded provenance is unauditable, so adding a
    file without a provenance entry fails here.
    """

    provenance = (FIXTURES_V4 / 'PROVENANCE.md').read_text(encoding='utf-8')
    vendored = sorted(path.name
                      for path in FIXTURES_V4.rglob('*')
                      if path.is_file() and path.name != 'PROVENANCE.md')

    assert vendored, 'no vendored files found'
    for name in vendored:
        assert name in provenance, f'{name} is vendored but not recorded in PROVENANCE.md'
