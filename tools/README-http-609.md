# Residual HTTP and Resource literal checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_wire_residuals_609.py` covers the uncovered serialization residuals
of issue 609: the extra quote in the Resource GET response, the Version PATCH
response map's closing delimiter, and five Resource request member/comma defects.

It discovers and strictly parses all **29** actual Resource request bodies
(the baseline parses 24), using the existing duplicate-key guard from
`test_samples.py`. It also checks the repaired requests' Meta nesting, boolean
values, unknown-ID scenario and abbreviated year strings without changing their
processing semantics. Source-derived malformed variants still fail JSON parsing.

The HTTP Resource GET body is parsed without preprocessing. The abbreviated
Version response removes only its three explicitly designated omitted-field
comments and the commas introducing those omissions. The remaining map is
strict JSON and is compared with actual request IDs and label objects.
The request's independently covered trailing commas are not silently repaired.

## Existing live coverage

[xregistry/spec#657](https://github.com/xregistry/spec/pull/657), inspected at
head `331b33aee45069fa833e174430d6c123e3c7f0cd`, already covers all six private-name
header encodings, the Resource POST response comma, three Version PATCH request
commas, and the single-Version PUT request/response commas. None of those edits
is duplicated here. A separate read-only check of that immutable upstream source
confirmed the six encodings match its actual JSON names and the four affected
bodies parse after removing only designated omitted-document comments.

No prior PR changes are copied into this branch. These checks do not validate
final-state pseudonotation, ancestry/default-selection policy, metadata-view
semantics, a running server or interoperability.

Run from the repository root:

```console
python -B -m pytest tools/test_http_wire_residuals_609.py -q -p no:cacheprovider
```
