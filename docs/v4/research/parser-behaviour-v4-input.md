# What happens today when v4 metadata meets this v2 client

**Measured**, not assumed. Reproduce with
[`../fixtures/trippin-v4-metadata.xml`](../fixtures/trippin-v4-metadata.xml)
against `pyodata` at commit `c8258ee`.

```python
from pyodata.v2.model import MetadataBuilder, Config, PolicyWarning
xml = open('docs/v4/fixtures/trippin-v4-metadata.xml', 'rb').read()

MetadataBuilder(xml).build()                                        # strict
MetadataBuilder(xml, config=Config(default_error_policy=PolicyWarning())).build()
```

## Headline finding

The v4 EDMX and EDM namespaces are **already on the whitelist**
(`pyodata/v2/model.py:2702-2713`). A v4 document therefore sails past the only
version gate the library has and is parsed as if it were v2. There is no
"unsupported version" error anywhere in the code path.

The result is not a clean failure. It is a **mix of hard errors and silent data
loss**, and the silent half is the dangerous half.

## Strict mode (`PolicyFatal`, the default)

```
PyODataParserError: Type None is not valid as underlying type for EnumType -
must be one of {'Edm.Byte': ..., 'Edm.Int16': ..., 'Edm.Int32': ..., ...}
```

Parsing aborts on the first `EnumType`. The message names neither the file, the
enum, nor the actual cause (v4 makes `UnderlyingType` optional, defaulting to
`Edm.Int32`; `pyodata/v2/model.py:1606` reads it and `:1616` rejects `None`).

## Permissive mode (`PolicyWarning`)

Parsing completes and returns `Schema(Trippin)` with `is_valid == False`. Two
warnings are emitted:

```
[PyODataParserError] Type None is not valid as underlying type for EnumType - ...
[AttributeError] 'NoneType' object has no attribute 'split'
```

The second is `Identifier.parse(None)` at `pyodata/v2/model.py:2006` —
`NavigationTypeProperty.from_etree` reads the v2 `Relationship` attribute, which
does not exist in v4. Every entity type that declares a navigation property
becomes a `NullType`.

What the caller gets back:

```
entity_types:     ['Person', 'Trip', 'Employee']      # Person is a NullType
complex_types:    ['Location']                        # correct
enum_types:       ['PersonGender']                    # a NullType
entity_sets:      ['People']
function_imports: ['GetNearestAirport']
associations:     []                                  # v4 has none — correct but load-bearing
association_sets: []

s.entity_type('Person')  ->  PyODataModelError: Cannot access this type.
                             An error occurred during parsing ... replaced with NullType.

s.entity_type('Trip').proprties()
  ->  [('TripId', 'Edm.Int32'), ('StartsAt', 'Edm.DateTimeOffset')]   # correct!
```

## Failure catalogue

Ranked by danger. **Silent** entries produce a schema that looks usable and is not.

| # | v4 construct | Today's behaviour | Severity |
|---|---|---|---|
| 1 | `<FunctionImport Function="Ns.Fn">` | Parsed. `return_type_info=None`, `parameters=[]`, `http_method=None`, because in v4 the signature lives on the schema-level `<Function>`, not the import. A call returns `None` and swallows the response body. | **Silent, severe** |
| 2 | `<EntityType BaseType="Ns.Person">` | Parsed. Inherited properties and keys are simply absent — `Employee` came back with `Cost` only. No warning. | **Silent, severe** |
| 3 | `<Singleton Name="Me">` | Not matched by any xpath. Vanishes. | **Silent** |
| 4 | Schema-level `<Function>` / `<Action>` | Not matched by any xpath. Vanish. | **Silent** |
| 5 | `<TypeDefinition>` | Not matched by any xpath. Properties typed by it will later fail to resolve. | **Silent** |
| 6 | `<NavigationPropertyBinding Path Target>` | Ignored. `EntityProxy.nav()` resolves targets through `AssociationSet` (`v2/service.py:943-969`, via `association_set_by_association` at `:955`), which v4 does not have — navigation is structurally impossible. | **Silent** |
| 7 | `ContainsTarget="true"` (containment) | Ignored. | Silent |
| 8 | Inline `<Annotation Term=...>` | Ignored. Only external `<Annotations>` groups carrying SAP value-list terms are read (`v2/model.py:1430-1462`). All v4 vocabulary annotations are lost. | Silent |
| 9 | `edmx:Edmx/@Version="4.0"` | Never read. | Silent |
| 10 | `<NavigationProperty Type Partner>` | `AttributeError` -> entity becomes `NullType`. | Loud |
| 11 | `<EnumType>` without `UnderlyingType` | `PyODataParserError`. | Loud |
| 12 | `Edm.Date`, `Edm.TimeOfDay`, `Edm.Duration`, `Edm.Stream`, `Edm.Geography*` | Absent from the `Types` registry — `KeyError` on resolution. Confirmed missing. | Loud |

## Two pre-existing v2 defects found while measuring

Unrelated to v4, but they sit in code the v4 work will touch, and the fork should
fix them on the v2 side first (as v2 fixes, with v2 tests) so that v4 does not
inherit them:

1. **`pyodata/v2/model.py:1634`** — enum member range check is
   `if not vtype[0] < next_value < vtype[1]`. Strict inequality rejects the
   boundary values. An `Edm.Byte` enum member with value `0` or `255`, or an
   `Edm.Int32` member at `INT32_MIN`/`INT32_MAX`, raises `PyODataParserError`
   even though the value is legal. Should be `<=`.
2. **`pyodata/v2/service.py:1329`** — `GetEntitySetFilterChainable._build_expression`
   emits `f'{field} gte {low} and {field} lte {high}'` for the `__range` lookup.
   `gte` and `lte` are not OData operators in *any* version; the correct tokens
   are `ge` and `le`. The `__range` lookup produces a `$filter` that no compliant
   server will accept. (The `__gte` / `__lte` lookups a few lines above correctly
   emit `ge` / `le`, so this is a typo, not a convention.)

## Conclusion for the design

The library cannot be made to "just work" with v4 by loosening parsers. The
object graph itself is v2-shaped: `Association` / `AssociationSet` /
`EndRole` are *required* for navigation, and v4 has no such concept. Navigation,
operations, and inheritance are structural differences, not formatting
differences. This is the evidence base for the decision in
[`../plan/architecture.md`](../plan/architecture.md).
