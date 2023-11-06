# xRegistry Primer

Possible future topics to cover:
- Resource.ID and Resource.Version.ID might have the same values but they are
  very different properties with no relation to each other.
- we require all extensions (and therefore all attributes) to be defined by
  the "model" so that we know their true serialization (case) even if we see
  them in a case insensitive serialization (e.g. HTTP headers)
- we use xxx/yyy/zzz for filters instead of xxx.yyy.zzz so that people have
  a consistent pattern when traversing the registry try. Meaning, it would
  be a bit odd for people to write:
  - `GET .../xxx/yyy/zzz` to reference a nested resource
  - but then `GET ...?filter=xxx.yyy.zzz.prop=5` to access a property on that
    same nested resources. So, despite some people might thinking that it's
	odd to see `/` in a query parameter, the consistency was more important
	to us. People can now copy-n-paste the same ref string in both uses.
- "latest" Resource is just a pointer, NOT a set of default values
- we allow for implicit creation of a resource's tree rather than requiring
  multiple create operations - just for convinience
- if/when we support serializing in non-json formats, we'll need to define
  the serialization rules. E.g. when attributes appear as xml attributes vs
  nested elements

