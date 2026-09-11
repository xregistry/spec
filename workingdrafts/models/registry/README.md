# Registry-of-Registries Service - Version 1.0-rc1

<!-- words: federationprofiles readme registrytypes website weburl xregurl -->

**Status:** Unreleased working draft using xRegistry Core 1.0-rc4. This
domain is not part of a released xRegistry specification.

The [specification](spec.md) defines a catalog of versioned, metadata-only
Registry descriptions. The [authoritative model](model.json) preserves the
hub's `categories` / `registries` hierarchy and OPTIONAL `weburl` and
`xregurl`. Labels, `registrytypes` and `federationprofiles` are OPTIONAL.
A website-only entry is a valid catalog entry, not a federation endpoint.

See the [full examples](samples/README.md) for base entries, multiple
bindings and descriptive relationships. [Derived schemas](schemas/README.md)
include JSON Schema, JSON Structure, Avro and HTTP OpenAPI descriptions,
with reproducible generation commands and current generator limitations.

[Shared federation](../../federation/spec.md) defines read-only resolution
after catalog selection.
[Base and resolvable conformance](spec.md#10-conformance) are distinct.
An advertisement does not establish reachability or trust.
