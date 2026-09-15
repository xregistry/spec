# Typed wildcards on named JSON Structure objects

<!-- no verify-specs -->
<!-- words: validators altnames additionalproperties sdk -->

A modeled object with named properties and a typed `*` retains both contracts.
The generator emits the wildcard's value schema in `additionalProperties`;
the named properties keep their own types, alternate names and required flags.
Object wildcard values use the existing named-definition/reference mechanism,
including their nested field constraints.

For example, an object with required string `name` and integer `*` accepts
`{"name":"http","count":7}` but rejects a string `count`, a non-string `name`,
or a missing `name`. No wildcard still means a closed object. An `any`
wildcard retains its existing open boundary.

This follows the [primary additional-properties contract][additional].
It changes generated type descriptions for previously rejected, model-admitted
values. Consumers should regenerate their types and enforce the wildcard value
schema, not treat its presence as permission for arbitrary values.

The tests exercise a bounded translation of these Core dialect constructs,
not a complete JSON Structure SDK. Core name admission, conditional activation
and numeric representation policies remain separate. This change does not
redefine wholly dynamic or closed-empty objects.

[additional]: https://github.com/json-structure/core/blob/7371ab90b6cc5bed72df95bd35c715ee11304b82/draft-vasters-json-structure-core.md#L1338-L1355
