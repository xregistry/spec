# WoT Registry Resolution Vectors

<!-- words: allowprerelease bytewise contentdigest gitattributes hashlib hexdigest iterdir minversion pathlib prereleases py submodel typelinks versionorigin workingdrafts wotid -->

The checker runs 64 numbered JSON files against the reference implementation.
Each file defines one case. [Section 1.3](../../spec.md#13-versioning)
describes behavior that these cases exercise. The checker also tests the
resolver against [Section 5.4](../../spec.md#54-versioned-reference-resolution).
The `sha256:` values are syntactically valid placeholders, not digests of
WoT documents.
`MANIFEST.sha256` hashes the committed bytes of every file in this directory
except itself, including this README, the schema, and the checker.

## Running the checker

From the repository root:

```sh
python workingdrafts/models/wot/tests/resolution/check_vectors.py
```

The script performs these checks:

1. It verifies manifest coverage and hashes, and requires LF and a final
   newline in every file.
2. If the Python environment includes `jsonschema`, it validates the schema
   and vectors.
3. It runs the reference implementation against every expected result.

When `jsonschema` is unavailable, the script reports that it skipped shape
validation. It still runs the semantic cases. When a check fails, the script
exits with a nonzero code. All other checks use Python's standard library.
The script does not fetch schemas or documents.

## Format

schema.json defines the format with JSON Schema draft 2020-12 and rejects
unknown fields. The top-level fields are:

| Field | Meaning |
|---|---|
| `description` | Explains what the case tests. |
| `registry` | Resource snapshots keyed by `wotid`, each with a default selection and its Versions. |
| `reference` | Resolution request with a `kind`, target `wotid`, and OPTIONAL `minVersion` and `floorTerm`. |
| `document` | OPTIONAL Thing Description (TD) context for Thing Model (TM) `rel:type` links, with `version.model` and `typeLinks`. |
| `publish` | Publication request with `target` and OPTIONAL `versionid`, `targetKind`, `version.model`, and `version.instance`. |
| `pin` | Caller pin: exactly one of `{ "digest": "sha256:..." }` or `{ "versionid": "1.0.0" }`. |
| `allowPrerelease` | OPTIONAL caller flag that allows prerelease selection. By default, its value is `false`. |
| `expect` | Exactly one resolution `result`, publication `assigned`, or `error`. |

The `reference.kind` field identifies the operator:

- `extends`, `submodel`, `ref`, and `type` identify TM or type-link operators.
- `td-extends`, `td-subthing`, and `td-ref` identify TD-to-TD operators.

`minVersion` holds the normalized floor. When present, `floorTerm` records
whether the input used `tm:minVersion` or `td:minVersion`. The checker uses
that term to reject a floor attached to the wrong target kind. When the caller
omits both properties, the checker uses the term expected for `kind`. When
`publish.targetKind` is `"td"`, publication uses `version.instance`. Otherwise,
the request targets a TM and uses `version.model`.

Every entry in `registry[].versions` has `versionid`, `versionorigin`, and
`contentdigest`. The `versionorigin` field accepts `authored` or
`generated`. The entry also has OPTIONAL `version.model` or
`version.instance`. A Resource MAY include
`deprecated: { "alternative": "https://..." }`. Stored snapshots use valid
SemVer version ids without build metadata.
`defaultversionid` MAY be null for an empty Resource awaiting publication. A
vector can set the sticky default to a Version absent from `versions` to test
`not-found`. A conforming Core write would not create that state.

The JSON keys `version.model` and `version.instance` name nested members in
WoT documents. For `ref`, `target` holds the document identifier after URI
resolution and fragment removal. Fragment traversal is outside these
version-selection cases. Fixture checks do not transform stored documents.

For a `type` reference, `document.typeLinks` lists the TD's type links. The
request MUST project exactly one link by `target`, including its explicit
`minVersion` if any.

The checker applies these floor rules:

- With one type link, the checker uses the greater of its explicit floor and
  `version.model` when both are present.
- With several type links and `version.model`, every link needs an
  explicit floor. Otherwise, the checker returns `ambiguous-floor`.
- Without `version.model`, the checker uses each type link's own floor, if
  present.

TD-to-TD references do not inherit an implicit floor.

A TD floor `X.Y.Z` sets the upper limit to `(X+1).0.0`, exclusive. Candidates
at or above that major, including prereleases, are out of range. An unfloored
TD reference can cross majors. If a sticky default falls outside the range,
the checker returns `unsatisfied`. Each fixture's `registry` array contains
at most one Resource per `wotid`. Resolve any matches across registries and
Groups before building the fixture.

A successful resolution returns the portable fields `wotid`, `versionid`,
and `contentdigest`. The production resolver also returns `origin`. That
value describes resolver context, not authored document data or a Resource
attribute. The checker fixes the origin as `https://registry.example` and
checks it before comparing the portable fields. Consumers MUST retain the
actual registry origin in production output.

A successful publication returns `versionid`, `versionorigin`, and
`defaultversionid`. Each request targets an existing Resource snapshot. A
snapshot with no Versions represents creation. The returned default is Core's
post-publication default, not the resolver's prerelease-filtered choice. The
cases assign TM or TD Version ids and select that default. They do not test
document compatibility validation or Core HTTP envelopes. The input schema
accepts syntactically invalid values so the cases can check the corresponding
domain errors.

An error expectation uses `{ "error": "<name>" }`. The name is one of:

- `not-found`
- `pin-mismatch`
- `unsatisfied`
- `ambiguous-floor`
- `invalid-floor`
- `version-mismatch`
- `invalid-version`

When a caller supplies a pin, the resolver ignores:

- Floors
- Sticky selection
- The TD major cap
- Prerelease filtering

Otherwise, a sticky default is authoritative and MUST be in range.
Without a sticky default, the highest eligible SemVer wins. Generated
`0.0.0-N` ids are prereleases and are never valid floors.

## TD-to-TD vectors (050–064)

| File | Case |
|---|---|
| `050-td-caret-within-major.json` | The resolver selects the highest eligible TD version below the next major. |
| `051-td-caret-excludes-next-major.json` | The resolver excludes a candidate at the next-major boundary. |
| `052-td-unfloored-crosses-majors.json` | The resolver allows an unfloored TD reference to cross majors. |
| `053-td-sticky-higher-major-unsatisfied.json` | The resolver rejects a sticky default in a higher major. |
| `054-td-floor-unmet.json` | The resolver returns `unsatisfied` when no TD version meets the floor. |
| `055-td-prerelease-floor.json` | The resolver admits eligible prereleases within the caret range. |
| `056-td-ref-floor.json` | The resolver applies the sibling floor to `td:ref`. |
| `057-td-subthing-floor.json` | The resolver applies a major-zero floor to `td:subthing`. |
| `058-td-publish-authored-assignment.json` | The publisher assigns the authored identity from `version.instance`. |
| `059-td-publish-generated-id.json` | The publisher assigns the lowest unused generated id. |
| `060-td-publish-version-mismatch.json` | The publisher rejects a supplied id that differs from `version.instance`. |
| `061-td-publish-build-metadata.json` | The publisher rejects build metadata in `version.instance`. |
| `062-td-minversion-on-tm-reference-invalid-floor.json` | The resolver rejects `td:minVersion` on a TM reference as an invalid floor. |
| `063-tm-minversion-on-td-reference-invalid-floor.json` | The resolver rejects `tm:minVersion` on a TD reference as an invalid floor. |
| `064-td-extends-floor.json` | The resolver applies the floor to `td:extends`. |

## Canonical bytes and maintenance

All files use UTF-8 without a byte-order mark, LF, and a final newline.
JSON files use two-space indentation. The manifest sorts filenames in bytewise
order. Each line contains `<lowercase-sha256>  <filename>`.
The repository's `.gitattributes` pins LF in Windows checkouts because the
manifest hashes exact bytes. Fixtures and the manifest contain no timestamps
or absolute local paths.

After an intentional edit, run this snippet from the repository root to
regenerate the manifest. Then run the checker:

```python
from hashlib import sha256
from pathlib import Path

folder = Path("workingdrafts/models/wot/tests/resolution")
files = sorted((p for p in folder.iterdir() if p.is_file() and p.name != "MANIFEST.sha256"), key=lambda p: p.name)
text = "".join(f"{sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files)
(folder / "MANIFEST.sha256").write_text(text, encoding="ascii", newline="\n")
```

You can test semantic validation with these steps:

1. You change an expected outcome to another schema-valid value.
2. You regenerate the manifest so the checker reaches semantic validation.
3. You run the checker. The test requires the checker to fail.
4. Both the vector and manifest MUST then be restored byte for byte and the
   checker rerun.

To test byte verification, you change one file byte without updating its hash.
That byte mutation MUST fail manifest verification.
