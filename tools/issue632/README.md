# Message duration profile checks

<!-- words: pytest dayTimeDuration cacheprovider py SDK -->

`day_time_duration_632.py` is an offline, exact rational value-space model of
the Message duration profile. `test_day_time_duration_632.py` parses the actual
duration table in the [Message specification](../../message/spec.md), checks
equivalent values, signs, fractions, malformed inputs, and separate field
bounds. Run from the repository root:

```shell
python -B -m pytest tools/issue632 -q -p no:cacheprovider
```

The grammar follows the normative productions for
[XML Schema duration](https://www.w3.org/TR/xmlschema11-2/#duration) and
[dayTimeDuration](https://www.w3.org/TR/xmlschema11-2/#dayTimeDuration),
including the unsigned decimal production for seconds. The reference model
accepts fractional seconds with an omitted integer or fractional part, such as
`PT.5S` and `PT1.S`, as those productions allow. It does not impose the
canonical representation's component limits on the lexical space.

These checks are abstract/source evidence, not server or SDK interoperability.
The helper is not a general XML Schema processor, does not acquire schemas,
and does not define native wire encodings. Its bounds model a field
definition that narrows the duration value space; they do not add new
declaration attributes. Existing integer duration fields are not converted.
