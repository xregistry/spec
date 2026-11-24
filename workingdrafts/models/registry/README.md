# Registry-of-Registries Service - Version 1.0-rc1

<!-- words: federationprofiles pytest readme registrytypes website weburl workingdrafts xregurl -->

**Status:** Unreleased working draft using xRegistry Core 1.0-rc4. This
domain is not part of a released xRegistry specification.

The [specification](spec.md) defines a catalog whose entries are versioned,
metadata-only descriptions of Registries. The [authoritative model](model.json)
uses the `categories` / `registries` hierarchy. The human-facing website
(`weburl`) and the described Registry's HTTP API root (`xregurl`) are
OPTIONAL. Labels, `registrytypes` and `federationprofiles` are
also OPTIONAL. A website-only entry is valid catalog data; it does not provide
a federation endpoint.

See the [full examples](samples/README.md) for base entries, multiple
bindings and descriptive relationships. [Derived schemas](schemas/README.md)
include JSON Schema, JSON Structure, Avro and HTTP OpenAPI descriptions,
with reproducible generation commands and current generator limitations.

[Shared federation](../../federation/spec.md) defines read-only resolution
after catalog selection.
[Base and resolvable conformance](spec.md#10-conformance) are separate claims.
The base catalog can store entries without access methods. A resolvable
entry requires an advertisement usable by the Consumer under its binding
support and policy. Advertising access does not establish reachability
or trust.

The [tools directory](tools) contains this model's conformance tests.
Run them from the repository root in PowerShell:

```powershell
python -B -m pytest workingdrafts\models\registry\tools -q
```
