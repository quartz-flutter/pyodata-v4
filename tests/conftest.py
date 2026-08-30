"""PyTest Fixtures"""
import json
import logging
import os

import pytest
import yaml

from pyodata.v2.model import schema_from_xml, Types


def contents_of_fixtures_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    path_to_file = os.path.join(current_directory, file_name)

    with open(path_to_file, 'rb') as md_file:
        return md_file.read()


ABNF_TESTCASES_FILE = 'fixtures/v4/abnf/odata-abnf-testcases.yaml'


class _ODataLiteralLoader(yaml.SafeLoader):
    """A YAML loader that leaves every plain scalar as text.

    The ABNF corpus is a corpus of OData URL fragments, and YAML's implicit
    resolvers actively damage them: "0000-01-01" is a legal Edm.Date literal
    but not a Python date (safe_load raises "year 0 is out of range" on it),
    and an Input of "true" or "42" would arrive as a bool or an int rather
    than the text the grammar is about. Dropping the implicit resolvers makes
    every scalar a str, which is what a grammar corpus means.
    """


_ODataLiteralLoader.yaml_implicit_resolvers = {}


def load_abnf_testcases():
    """Load the vendored OASIS ABNF test-case corpus.

    Returns the list of vectors, each a dict with at least 'Rule' and 'Input'.
    A vector carrying 'FailAt' is a negative case, and its value -- the
    character offset at which parsing must fail -- is returned as an int;
    every other value is text.

    The corpus is vendored byte-exact from oasis-tcs/odata-abnf (see
    tests/fixtures/v4/PROVENANCE.md), which means it contains one deliberate
    raw tab: the vector proving a tab separates "$orderby=Name<TAB>asc".
    PyYAML's scanner refuses a tab in that position, so any scalar containing
    one is rewritten here into an equivalent double-quoted form before
    parsing. json.dumps produces exactly that (a JSON string is a valid YAML
    double-quoted scalar) and round-trips the tab, so the vector reaches the
    caller intact rather than being silently normalised away.
    """

    lines = contents_of_fixtures_file(ABNF_TESTCASES_FILE).decode('utf-8').split('\n')

    for index, line in enumerate(lines):
        if '\t' not in line:
            continue
        key, _, value = line.partition(': ')
        lines[index] = f'{key}: {json.dumps(value)}'

    testcases = yaml.load('\n'.join(lines), Loader=_ODataLiteralLoader)['TestCases']

    for testcase in testcases:
        if 'FailAt' in testcase:
            testcase['FailAt'] = int(testcase['FailAt'])

    return testcases


@pytest.fixture
def metadata():
    """Example OData metadata"""
    return contents_of_fixtures_file("metadata.xml")


@pytest.fixture
def xml_builder_factory():
    """Skeleton OData metadata"""

    class XMLBuilder:
        """Helper class for building XML metadata document"""

        # pylint: disable=too-many-instance-attributes,line-too-long
        def __init__(self):
            self.reference_is_enabled = True
            self.data_services_is_enabled = True
            self.schema_is_enabled = True

            self.namespaces = {
                'edmx': "http://schemas.microsoft.com/ado/2007/06/edmx",
                'sap': 'http://www.sap.com/Protocols/SAPData',
                'edm': 'http://schemas.microsoft.com/ado/2008/09/edm',
                'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
                'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
            }

            self.custom_edmx_prologue = None
            self.custom_edmx_epilogue = None

            self.custom_data_services_prologue = None
            self.custom_data_services_epilogue = None

            self._reference = '\n<edmx:Reference xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Uri="https://example.sap.corp/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Vocabularies(TechnicalName=\'%2FIWBEP%2FVOC_COMMON\',Version=\'0001\',SAP__Origin=\'LOCAL\')/$value">' + \
                              '\n<edmx:Include Namespace="com.sap.vocabularies.Common.v1" Alias="Common"/>' + \
                              '\n</edmx:Reference>'

            self._schemas = ''

        def add_schema(self, namespace, xml_definition):
            """Add schema element"""
            self._schemas += f""""\n<Schema xmlns:d="{self.namespaces["d"]}" xmlns:m="{self.namespaces["m"]}" xmlns="{
            self.namespaces["edm"]}" Namespace="{namespace}" xml:lang="en" sap:schema-version="1">"""
            self._schemas += "\n" + xml_definition
            self._schemas += '\n</Schema>'

        def serialize(self):
            """Returns full metadata XML document"""
            result = self._edmx_prologue()

            if self.reference_is_enabled:
                result += self._reference

            if self.data_services_is_enabled:
                result += self._data_services_prologue()

            if self.schema_is_enabled:
                result += self._schemas

            if self.data_services_is_enabled:
                result += self._data_services_epilogue()

            result += self._edmx_epilogue()

            return result

        def _edmx_prologue(self):
            if self.custom_edmx_prologue:
                prologue = self.custom_edmx_prologue
            else:
                prologue = f"""<edmx:Edmx  xmlns:edmx="{self.namespaces["edmx"]}" xmlns:m="{self.namespaces["m"]}" xmlns:sap="{self.namespaces["sap"]}" Version="1.0">"""
            return prologue

        def _edmx_epilogue(self):
            if self.custom_edmx_epilogue:
                epilogue = self.custom_edmx_epilogue
            else:
                epilogue = '\n</edmx:Edmx>'
            return epilogue

        def _data_services_prologue(self):
            if self.custom_data_services_prologue:
                prologue = self.custom_data_services_prologue
            else:
                prologue = '\n<edmx:DataServices m:DataServiceVersion="2.0">'
            return prologue

        def _data_services_epilogue(self):
            if self.custom_data_services_epilogue:
                prologue = self.custom_data_services_epilogue
            else:
                prologue = '\n</edmx:DataServices>'
            return prologue

    return XMLBuilder


@pytest.fixture
def schema(metadata):
    """Parsed metadata"""

    # pylint: disable=redefined-outer-name

    return schema_from_xml(metadata)


def assert_logging_policy(mock_warning, *args):
    """Assert if an warning was outputted by PolicyWarning """
    assert logging.Logger.warning is mock_warning
    mock_warning.assert_called_with('[%s] %s', *args)


def assert_request_contains_header(headers, name, value):
    assert name in headers
    assert headers[name] == value


@pytest.fixture
def type_date_time():
    return Types.from_name('Edm.DateTime')


@pytest.fixture
def type_date_time_offset():
    return Types.from_name('Edm.DateTimeOffset')
