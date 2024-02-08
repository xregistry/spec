# xRegistry Primer

Possible future topics to cover:
- Resource.ID and Resource.Version.ID might have the same values but they are
  very different properties with no relation to each other.
- it's RECOMMENDED that all extensions be defined in advance as part of the
  model. However, the spec does support an extension of "*" to allow for
  unknown/runtime-provided extensions. Since extensions can appear in case-
  insensitive situations (e.g. http header) we can't know the case of them
  when storing in the backend. As a result, all attributes and keyNames MUST
  be lowercase.
- "latest" Resource is just a pointer, NOT a set of default values
- we allow for implicit creation of a resource's tree rather than requiring
  multiple create operations - just for convinience
- if/when we support serializing in non-json formats, we'll need to define
  the serialization rules. E.g. when attributes appear as xml attributes vs
  nested elements
- when hasdocument=false, we might need to talk about when ?meta appears on the
  various URLs (self, latestversionurl, location,...). Right now its presence
  will match what was used in the request (either explicitly or implicity).
  So GET resource?meta or GET group?inline both ask for metadata
