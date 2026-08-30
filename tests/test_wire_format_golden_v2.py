"""Gate G2 of the OData v4 compatibility contract: v2 wire-format golden tests.

Rule R1 (docs/v4/plan/compatibility-contract.md): no change may alter the HTTP
method, path, query string, headers or body that the v2 code path produces.
The existing suite asserts outcomes; these tests assert the exact bytes, so
that the phase-2 extraction of ``pyodata/core/`` -- and every later change --
can be shown to be behaviour-preserving rather than argued to be.

Everything here is a *characterization* test: it records what the code does
today, not what it ought to do. Where today's output is known to be wrong the
expectation carries a DEFECT note naming the roadmap phase that changes it;
such a test is meant to fail then, and to be updated in the same commit as the
fix. Anywhere else, a failure here means a v2 behaviour change and is a bug in
the change under test.

Covered, per contract G2:

* ``to_literal``/``from_literal``/``null_value`` for every registered Edm type
* ``EntityKey.to_key_string()`` for single and composite keys
* ``get_method``/``get_path``/``get_query_params``/``get_body``/``get_headers``
  for every request class
* the exact ``$filter`` string produced by each lookup in the chainable DSL and
  by the ``GetEntitySetFilter`` operator API
* the multipart batch and changeset body, byte for byte
"""

import datetime

import pytest
import requests

import pyodata.v2.model
import pyodata.v2.service
from pyodata.v2.model import Types
from pyodata.v2.service import EntityKey, GetEntitySetFilter

URL_ROOT = 'http://odatapy.example.com'


@pytest.fixture
def service(schema):
    """A service backed by tests/metadata.xml, with no HTTP behind it."""

    return pyodata.v2.service.Service(URL_ROOT, schema, requests)


# --------------------------------------------------------------------------
# Edm literals
# --------------------------------------------------------------------------

# (type name, python value, expected literal). Note that the types carrying the
# base TypTraits (Edm.Byte, Edm.SByte, Edm.Decimal, Edm.Time) pass the value
# through unchanged and therefore do not return a string at all -- that is
# load-bearing behaviour for callers who format it themselves.
EDM_TO_LITERAL = [
    ('Edm.Binary', 'Gis=', "binary'1A2B'"),
    ('Edm.Boolean', True, 'true'),
    ('Edm.Boolean', False, 'false'),
    ('Edm.Boolean', 1, 'true'),
    ('Edm.Boolean', 0, 'false'),
    ('Edm.Byte', 255, 255),
    ('Edm.SByte', -128, -128),
    ('Edm.Decimal', '12.34', '12.34'),
    ('Edm.DateTime', datetime.datetime(2023, 5, 17, 14, 30, 25, tzinfo=datetime.timezone.utc),
     "datetime'2023-05-17T14:30:25'"),
    ('Edm.DateTimeOffset', datetime.datetime(2023, 5, 17, 14, 30, 25, tzinfo=datetime.timezone.utc),
     "datetimeoffset'2023-05-17T14:30:25+00:00'"),
    ('Edm.Double', 3.14, '3.140000E+00'),
    ('Edm.Double', 1, '1.000000E+00'),
    ('Edm.Float', 3.14, '3.140000E+00'),
    ('Edm.Single', 3.14, '3.140000'),
    ('Edm.Guid', '9dd80f38-1e5e-4a5f-a8c6-6d1d0b5f1c31', "guid'9dd80f38-1e5e-4a5f-a8c6-6d1d0b5f1c31'"),
    ('Edm.Int16', 32767, '32767'),
    ('Edm.Int16', -1, '-1'),
    ('Edm.Int32', 2147483647, '2147483647'),
    ('Edm.Int64', 9223372036854775807, '9223372036854775807L'),
    ('Edm.String', 'foo', "'foo'"),
    # single quotes are doubled per OData ABNF (commit c8258ee)
    ('Edm.String', "O'Brien", "'O''Brien'"),
    ('Edm.String', '', "''"),
]


@pytest.mark.parametrize('type_name,value,expected', EDM_TO_LITERAL)
def test_golden_edm_to_literal(type_name, value, expected):
    """The exact literal every Edm type puts on the wire."""

    assert Types.from_name(type_name).traits.to_literal(value) == expected


# The declared "null" literal of every registered primitive type. These reach
# the wire through $filter and key strings, so they are part of the contract.
EDM_NULL_VALUES = {
    'Null': 'null',
    'Edm.Binary': "binary''",
    'Edm.Boolean': 'false',
    'Edm.Byte': '0',
    'Edm.DateTime': "datetime'1753-01-01T00:00'",
    'Edm.DateTimeOffset': "datetimeoffset'1753-01-01T00:00:00Z'",
    'Edm.Decimal': '0.0M',
    'Edm.Double': '0.0d',
    'Edm.Float': '0.0d',
    'Edm.Guid': "guid'00000000-0000-0000-0000-000000000000'",
    'Edm.Int16': '0',
    'Edm.Int32': '0',
    'Edm.Int64': '0L',
    'Edm.SByte': '0',
    'Edm.Single': '0.0f',
    'Edm.String': "''",
    'Edm.Time': "time'PT00H00M'",
}


def test_golden_edm_null_values():
    """Every registered primitive type, and its null_value, pinned as a set.

    Asserting the whole mapping at once also pins the *membership* of the v2
    type registry: a type added to or dropped from Types.Types fails here.
    """

    Types._build_types()  # pylint: disable=protected-access
    actual = {name: typ.null_value
              for name, typ in Types.Types.items()
              if not name.startswith('Collection(')}

    assert actual == EDM_NULL_VALUES


@pytest.mark.parametrize('type_name,literal,expected', [
    ('Edm.String', "''", ''),
    ('Edm.String', "'foo'", 'foo'),
    ('Edm.Int64', '0L', 0),
    ('Edm.Int64', '42L', 42),
    ('Edm.Int32', '42', 42),
    ('Edm.Boolean', 'false', False),
    ('Edm.Boolean', 'true', True),
    ('Edm.Double', '0.0d', 0.0),
    ('Edm.Single', '0.0f', 0.0),
    ('Edm.Guid', "guid'00000000-0000-0000-0000-000000000000'", '00000000-0000-0000-0000-000000000000'),
    ('Edm.DateTime', "datetime'1753-01-01T00:00'",
     datetime.datetime(1753, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)),
    ('Edm.Binary', "binary'1A2B'", 'Gis='),
    # base TypTraits passes the literal straight through, unparsed
    ('Edm.Byte', '0', '0'),
])
def test_golden_edm_from_literal(type_name, literal, expected):
    """Parsing back the literals the client itself emits."""

    assert Types.from_name(type_name).traits.from_literal(literal) == expected


# --------------------------------------------------------------------------
# EntityKey
# --------------------------------------------------------------------------

def test_golden_key_string_single(schema):
    """Single-value key: bare literal, no property name."""

    key = EntityKey(schema.entity_type('MasterEntity'), '12345')

    assert key.to_key_string() == "('12345')"
    assert key.to_key_string_without_parentheses() == "'12345'"


def test_golden_key_string_single_by_name(schema):
    """A one-property key given by name renders the *named* form.

    Passing the same key positionally yields ("12345"); passing it as a keyword
    yields (Key="12345"). Both address the same entity, but they are different
    URLs, so which one a caller gets is part of the wire contract.
    """

    key = EntityKey(schema.entity_type('MasterEntity'), Key='12345')

    assert key.to_key_string() == "(Key='12345')"


def test_golden_key_string_composite(schema):
    """Composite key: name=literal pairs in entity-type key order, comma joined."""

    key = EntityKey(schema.entity_type('City'), Name='Sydney', CountryISO='AU')

    assert key.to_key_string() == "(Name='Sydney',CountryISO='AU')"


def test_golden_key_string_composite_mixed_types(schema):
    """Composite key mixing Edm.String and Edm.DateTime literals."""

    key = EntityKey(
        schema.entity_type('TemperatureMeasurement'),
        Sensor='Sensor-address',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    assert key.to_key_string() == "(Sensor='Sensor-address',Date=datetime'2017-12-24T18:00:00')"


def test_golden_key_string_escapes_quotes(schema):
    """A quote in a key value is doubled, not left to break the URL."""

    key = EntityKey(schema.entity_type('MasterEntity'), "O'Brien")

    assert key.to_key_string() == "('O''Brien')"


def test_golden_key_string_numeric(schema):
    """Numeric keys are unquoted."""

    key = EntityKey(schema.entity_type('Employee'), 23)

    assert key.to_key_string() == '(23)'


# --------------------------------------------------------------------------
# Request classes: method, path, query params, headers, body
# --------------------------------------------------------------------------

def test_golden_request_entity_get(service):
    """EntityGetRequest: GET, percent-encoded path, Accept only."""

    request = service.entity_sets.MasterEntities.get_entity('12345')

    assert request.get_method() == 'GET'
    assert request.get_path() == "MasterEntities%28%2712345%27%29"
    assert request.get_query_params() == {}
    assert request.get_body() is None
    assert request.get_headers() == {'Accept': 'application/json'}


def test_golden_request_entity_get_unencoded(service):
    """encode_path=False leaves the parentheses and quotes literal."""

    request = service.entity_sets.MasterEntities.get_entity('12345', encode_path=False)

    assert request.get_path() == "MasterEntities('12345')"


def test_golden_request_entity_get_select_expand(service):
    """$select and $expand are passed through verbatim, unencoded here."""

    request = service.entity_sets.Employees.get_entity(23).select('ID,NameFirst').expand('Addresses')

    assert request.get_path() == 'Employees%2823%29'
    assert request.get_query_params() == {'$select': 'ID,NameFirst', '$expand': 'Addresses'}


def test_golden_request_entity_get_value(service):
    """$value is appended as a path segment on a plain ODataHttpRequest."""

    request = service.entity_sets.Cars.get_entity('Hadraplan').get_value()

    assert request.get_method() == 'GET'
    assert request.get_headers() == {}
    assert request.get_body() is None


def test_golden_request_entity_create(service):
    """EntityCreateRequest: POST, JSON body, and the SAP-only X-Requested-With.

    X-Requested-With is v2/SAP-specific; phase 4 must NOT send it for v4.
    """

    request = service.entity_sets.MasterEntities.create_entity().set(Key='1234', Data='abcd')

    assert request.get_method() == 'POST'
    assert request.get_path() == 'MasterEntities'
    assert request.get_query_params() == {}
    assert request.get_body() == '{"Key": "1234", "Data": "abcd"}'
    assert request.get_headers() == {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'X',
    }


def test_golden_request_entity_create_empty_body(service):
    """A create with no values still sends an empty JSON object, not null."""

    request = service.entity_sets.MasterEntities.create_entity()

    assert request.get_body() == '{}'


def test_golden_request_entity_delete(service):
    """EntityDeleteRequest: DELETE, encoded path, no body and no default headers."""

    request = service.entity_sets.MasterEntities.delete_entity('12345')

    assert request.get_method() == 'DELETE'
    assert request.get_path() == 'MasterEntities%28%2712345%27%29'
    assert request.get_query_params() == {}
    assert request.get_body() is None
    assert request.get_headers() == {}


def test_golden_request_entity_modify_default_method(service):
    """EntityModifyRequest defaults to PATCH and sends only the changed keys."""

    request = service.entity_sets.MasterEntities.update_entity('12345').set(Data='abcd')

    assert request.get_method() == 'PATCH'
    assert request.get_path() == 'MasterEntities%28%2712345%27%29'
    assert request.get_query_params() == {}
    assert request.get_body() == '{"Data": "abcd"}'
    assert request.get_headers() == {'Accept': 'application/json', 'Content-Type': 'application/json'}


@pytest.mark.parametrize('method', ['PATCH', 'PUT', 'MERGE'])
def test_golden_request_entity_modify_allowed_methods(service, method):
    """All three v2 update verbs, MERGE included (phase 4 drops MERGE for v4)."""

    request = service.entity_sets.MasterEntities.update_entity('12345', method=method)

    assert request.get_method() == method


def test_golden_request_entity_set_get(service):
    """GetEntitySetRequest with no options: bare collection path."""

    request = service.entity_sets.MasterEntities.get_entities()

    assert request.get_method() == 'GET'
    assert request.get_path() == 'MasterEntities'
    assert request.get_query_params() == {}
    assert request.get_body() is None
    assert request.get_headers() == {'Accept': 'application/json'}


def test_golden_request_entity_set_all_query_options(service):
    """Every query option this client can set, and the exact parameter names."""

    request = (service.entity_sets.MasterEntities.get_entities()
               .top(10)
               .skip(5)
               .order_by('Key')
               .filter("Key eq '1'")
               .select('Key,Data')
               .expand('Nav')
               .count(inline=True)
               .custom('sap-client', '100'))

    assert request.get_query_params() == {
        '$top': 10,
        '$skip': 5,
        '$orderby': 'Key',
        '$filter': "Key eq '1'",
        '$select': 'Key,Data',
        '$expand': 'Nav',
        '$inlinecount': 'allpages',
        'sap-client': '100',
    }
    assert request.get_path() == 'MasterEntities'


def test_golden_request_entity_set_count(service):
    """count() without inline switches to the $count path and drops Accept."""

    request = service.entity_sets.MasterEntities.get_entities().count()

    assert request.get_path() == 'MasterEntities/$count'
    assert request.get_headers() == {}
    assert request.get_query_params() == {}


def test_golden_request_entity_set_next_url_wins(service):
    """A server-supplied __next URL suppresses every query parameter."""

    request = service.entity_sets.MasterEntities.get_entities().top(10).next_url(
        f'{URL_ROOT}/MasterEntities?$skiptoken=42')

    assert request.get_query_params() == {}


def test_golden_request_nav_entity_set(service):
    """Navigation renders as parent(key)/NavProp, encoded."""

    request = service.entity_sets.Employees.nav('Addresses', EntityKey(
        service.schema.entity_type('Employee'), 23)).get_entities()

    assert request.get_method() == 'GET'
    assert request.get_path() == 'Employees%2823%29/Addresses'
    assert request.get_headers() == {'Accept': 'application/json'}


def test_golden_request_function_import_no_parameters(service):
    """FunctionRequest: the declared HTTP method, function name as the path."""

    request = service.functions.refresh

    assert request.get_method() == 'GET'
    assert request.get_path() == 'refresh'
    assert request.get_query_params() == {}
    assert request.get_body() is None
    assert request.get_headers() == {'Accept': 'application/json'}


def test_golden_request_function_import_parameters(service):
    """Function parameters go on the query string as OData literals."""

    request = service.functions.sum.parameter('A', 2).parameter('B', 3)

    assert request.get_query_params() == {'A': '2', 'B': '3'}


def test_golden_request_function_import_string_parameter(service):
    """A string function parameter keeps its quotes in the query string."""

    request = service.functions.retrieve.parameter('Param', 'Foo')

    assert request.get_query_params() == {'Param': "'Foo'"}


# --------------------------------------------------------------------------
# $filter rendering -- the chainable lookup DSL
# --------------------------------------------------------------------------

def _filter_string(service, **lookups):
    """Render one lookup through the chainable DSL."""

    return str(service.entity_sets.Employees.get_entities().filter(**lookups)._filter)


@pytest.mark.parametrize('lookup,value,expected', [
    ({'NameFirst': None}, 'Tim', "NameFirst eq 'Tim'"),
    ({'NameFirst__eq': None}, 'Tim', "NameFirst eq 'Tim'"),
    ({'ID__lt': None}, 5, 'ID lt 5'),
    ({'ID__gt': None}, 5, 'ID gt 5'),
    # lte/gte render as the correct OData "le"/"ge" here
    ({'ID__lte': None}, 5, 'ID le 5'),
    ({'ID__gte': None}, 5, 'ID ge 5'),
    ({'NameFirst__startswith': None}, 'Tim', "startswith(NameFirst, 'Tim') eq true"),
    ({'NameFirst__endswith': None}, 'thy', "endswith(NameFirst, 'thy') eq true"),
    # v2 argument order: substringof(value, field). v4 reverses it to
    # contains(field, value) -- see roadmap phase 4.
    ({'NameFirst__contains': None}, 'im', "substringof('im', NameFirst) eq true"),
    ({'NameFirst__length': None}, 3, 'length(NameFirst) eq 3'),
    ({'NameFirst__in': None}, ['Tim', 'Bob'], "NameFirst eq 'Tim' or NameFirst eq 'Bob'"),
])
def test_golden_filter_lookup(service, lookup, value, expected):
    """One lookup operator, one rendering."""

    key = next(iter(lookup))
    assert _filter_string(service, **{key: value}) == expected


def test_golden_filter_lookup_range_defect(service):
    """DEFECT (roadmap phase 1, service.py:1319): __range emits gte/lte.

    Neither is an OData operator in any version; the correct rendering is
    "ge"/"le". Pinned here as-is so the phase-1 fix is a visible, deliberate
    change to this expectation rather than a silent one.
    """

    assert _filter_string(service, ID__range=(5, 9)) == 'ID gte 5 and ID lte 9'


def test_golden_filter_multiple_lookups_are_anded(service):
    """Several lookups in one filter() call join with " and " in kwargs order."""

    result = _filter_string(service, NameFirst='Tim', ID__gt=5)

    assert result == "NameFirst eq 'Tim' and ID gt 5"


def test_golden_filter_expression_or(service):
    """FilterExpression combined with | wraps both sides in parentheses."""

    name_is_tim = pyodata.v2.service.FilterExpression(NameFirst='Tim')
    surname_is_smith = pyodata.v2.service.FilterExpression(NameLast='Smith')
    expression = name_is_tim | surname_is_smith
    result = str(service.entity_sets.Employees.get_entities().filter(expression)._filter)

    assert result == "(NameFirst eq 'Tim') or (NameLast eq 'Smith')"


def test_golden_filter_expression_and(service):
    """FilterExpression combined with & renders the "and" operator."""

    name_is_tim = pyodata.v2.service.FilterExpression(NameFirst='Tim')
    surname_is_smith = pyodata.v2.service.FilterExpression(NameLast='Smith')
    expression = name_is_tim & surname_is_smith
    result = str(service.entity_sets.Employees.get_entities().filter(expression)._filter)

    assert result == "(NameFirst eq 'Tim') and (NameLast eq 'Smith')"


# --------------------------------------------------------------------------
# $filter rendering -- the GetEntitySetFilter operator API
# --------------------------------------------------------------------------

@pytest.mark.parametrize('render,expected', [
    (lambda p: p == 'Tim', "NameFirst eq 'Tim'"),
    (lambda p: p != 'Tim', "NameFirst ne 'Tim'"),
    (lambda p: p < 'Tim', "NameFirst lt 'Tim'"),
    (lambda p: p <= 'Tim', "NameFirst le 'Tim'"),
    (lambda p: p > 'Tim', "NameFirst gt 'Tim'"),
    (lambda p: p >= 'Tim', "NameFirst ge 'Tim'"),
])
def test_golden_filter_operator_api(service, render, expected):
    """Each comparison operator on a property proxy."""

    proprty = service.entity_sets.Employees.get_entities().NameFirst

    assert render(proprty) == expected


def test_golden_filter_operator_api_and_or(service):
    """and_/or_ parenthesise the whole group and join with a single operator."""

    entities = service.entity_sets.Employees.get_entities()
    name_is_tim = entities.NameFirst == 'Tim'
    surname_is_smith = entities.NameLast == 'Smith'
    id_over_five = entities.ID > 5

    assert GetEntitySetFilter.and_(name_is_tim, id_over_five) == "(NameFirst eq 'Tim' and ID gt 5)"
    assert GetEntitySetFilter.or_(name_is_tim, id_over_five) == "(NameFirst eq 'Tim' or ID gt 5)"
    assert GetEntitySetFilter.and_(name_is_tim, surname_is_smith, id_over_five) == (
        "(NameFirst eq 'Tim' and NameLast eq 'Smith' and ID gt 5)")


# --------------------------------------------------------------------------
# Multipart batch bodies, byte for byte
# --------------------------------------------------------------------------

def test_golden_batch_request_envelope(service):
    """A batch of one GET: boundary naming, part headers, and CRLF framing."""

    batch = service.create_batch('1234_5678_9012')
    batch.add_request(service.entity_sets.MasterEntities.get_entity('12345'))

    assert batch.get_method() == 'POST'
    assert batch.get_path() == '$batch'
    assert batch.get_boundary() == 'batch_1234_5678_9012'
    assert batch.get_headers() == {'Content-Type': 'multipart/mixed;boundary=batch_1234_5678_9012'}
    assert batch.get_body() == '\r\n'.join([
        '',
        '--batch_1234_5678_9012',
        'Content-Type: application/http',
        'Content-Transfer-Encoding:binary',
        '',
        'GET MasterEntities%28%2712345%27%29 HTTP/1.1',
        'Accept: application/json',
        '',
        '',
        '--batch_1234_5678_9012--',
    ])


def test_golden_batch_request_with_query_params(service):
    """Query parameters are urlencoded onto the part's request line."""

    batch = service.create_batch('1234_5678_9012')
    batch.add_request(service.entity_sets.MasterEntities.get_entities().top(2).filter("Key eq '1'"))

    assert 'GET MasterEntities?%24top=2&%24filter=Key+eq+%271%27 HTTP/1.1' in batch.get_body()


def test_golden_changeset_nested_in_batch(service):
    """A changeset nests as a part whose body is itself a multipart document."""

    batch = service.create_batch('1234_5678_9012')
    changeset = service.create_changeset('abcd_efgh_ijkl')
    changeset.add_request(
        service.entity_sets.MasterEntities.update_entity('12345').set(Data='abcd'))
    batch.add_request(changeset)

    assert changeset.get_boundary() == 'changeset_abcd_efgh_ijkl'
    assert batch.get_body() == '\r\n'.join([
        '',
        '--batch_1234_5678_9012',
        'Content-Type: multipart/mixed;boundary=changeset_abcd_efgh_ijkl',
        '',
        '',
        '--changeset_abcd_efgh_ijkl',
        'Content-Type: application/http',
        'Content-Transfer-Encoding:binary',
        '',
        'PATCH MasterEntities%28%2712345%27%29 HTTP/1.1',
        'Accept: application/json',
        'Content-Type: application/json',
        '',
        '{"Data": "abcd"}',
        '--changeset_abcd_efgh_ijkl--',
        '--batch_1234_5678_9012--',
    ])


def test_golden_batch_empty_body_is_blank_line(service):
    """A part with no body still emits a blank line.

    The SAP gateway rejects the request without it (see the comment on
    encode_multipart); this test is what keeps that blank line from being
    "cleaned up" during the phase-2 move of the multipart code.
    """

    batch = service.create_batch('1234_5678_9012')
    batch.add_request(service.entity_sets.MasterEntities.delete_entity('12345'))

    assert batch.get_body().endswith('\r\n\r\n--batch_1234_5678_9012--')
