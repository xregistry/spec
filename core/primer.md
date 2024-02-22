# xRegistry Primer

<!-- no verify-specs -->

## Design decisions

### Resource.ID vs Resource.Version.ID

Resources, like all xRegistry entities, have unique `id` values. Resource
`id`s are often user-friendly values that often have an implied semantic
meaning of the purpose of the underlying Resource document. Also, since they
are static values and as the Resource changes over time (meaning, new Versions
are created), it's important for end-users to have a static URL reference to
the latest Version of the Resource.

Versions of a Resource, on the other hand, might change quite often and the
`id` isn't meant to convey the purpose of the underlying entity, rather it is
meant to uniquely specify its "version number".  As such, the semantics
meaning and usage of the two `id` values are quite different. This means that
there might be times when they are the same value However, while this is
allowable, it has no influence on any specification defined semantics of the
xRegistry model. As a result, implementations might want to avoid using `id`
values that could appear on a Resource and one of its Versions simply to avoid
potential confusion for their end-users.

### Valid Characters

The xRegistry specification restricts the allowable characters for attribute
and map key names. While it can be considered overly restrictive, for example
uppercase characters are not permitted, this was done because considerations
had to be made to take into account where these names might appear.

Some of the challenges:
- attribute and key name might appear as HTTP headers, which are
  case insensitive. On the surface this would mean that simply not allowing
  more than one name of different cases would suffice. However, in the case
  of the name being part of a open-ended extension (e.g. allowable due to a
  `*` defined attribute), the server has no way of knowing its proper case.
  And when they're serialized in the HTTP body, case then matters.
- some network proxying software limit the allowable characters that can
  appear in HTTP header names by default. For example, nginx will drop all
  HTTP headers that include underscore (`_`) characters. While there are most
  likely configuration flags to disable this behavior, it might not always
  be possible (or easy) for xRegistry implementations to modify those
  networking components.
- often attribute names, or object property names, are mapped into code
  variable or properties within code structures. While many programming
  langugaes allow for a mapping from those names to their serialization
  names, often these mapping can introduce pain - either because they require
  additional work/configuration or simply due to errors being introduced
  by not using the language specific default mapping.

So rather than raising the bar for installation, maintenance, and debugging
(detecting the possible issues mentioned above), it was deemed better to
simply avoid the problem (and hopefully increase interoperability) by just
limiting the allowable characters.

Note though, map key names allow more characters than well-define object
attribute names because map key names are not usually mapped to well defined
variable or structure property names - they're usually just stored as
"strings" a map data structure.

### Extensions

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
- xRegistry- headers: first "-" separates xRegistry from attribute name,
  next "-" separates attribute name from key, any subsequent "-" is part
  of the key name. E.g xRegistry-labels-abc-def:xxx => labels["abc-def"]=xxx
- impact of "*required" flags at multiple levels
- why we don't use underscore in our property names, tho legal to do so
  - not all http proxies (e.g. nginx) pass them along by default
  - so, while spec allows underscores, use at your own risk
- discuss any potential semantic gotchas when one attribute is required
  but a nested attribute is optional, or also required (and visa-versa)
  - reminder: clientrequired=true means serverrequired=true as well, else error
