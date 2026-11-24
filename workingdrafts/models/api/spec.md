# API Registry Service - Version 0.1 (Working Draft)

<!-- words: abnf apigroup apigroupid apigroups apigroupscount apigroupsurl -->
<!-- words: apiid apiscount apisurl apiurl avroidl avroprotocol bcp -->
<!-- words: compatibilityvalidated compatibilityvalidatedreason -->
<!-- words: filedescriptorset formatvalidated formatvalidatedreason -->
<!-- words: getuserprofile getuserprofilerequest getuserprofileresponse -->
<!-- words: graphql graphqlintrospection grpc idl jsonc jsonrpc -->
<!-- words: matchversions modelschema namespace namespaces ncnames -->
<!-- words: nmtoken nmtokens oas oftype oneway openapis openrpc operationid -->
<!-- words: protocolbuffers qname qnames sdl smithyast smithyidl smithymodel -->
<!-- words: strictvalidation unversioned updateuserprofile userid -->
<!-- words: userprofile userprofileservice validatecompatibility -->
<!-- words: compatibilitiescapability formatscapability validateformat wsdl xmlsoap -->

## Abstract

This document defines an API Registry extension to the xRegistry
document format and API. An API Registry stores and manages versioned API
definition documents, primarily for synchronous request-response interfaces.

This working draft is dated September 15, 2026, and is not part of a released
xRegistry specification.

## Table of Contents

- [Abstract](#abstract)
- [Table of Contents](#table-of-contents)
- [Overview](#overview)
  - [API Documents and Schemas](#api-documents-and-schemas)
  - [Versioning](#versioning)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
  - [Terminology](#terminology)
    - [API](#api)
    - [API Document](#api-document)
    - [Operation](#operation)
    - [Operation Locator](#operation-locator)
    - [API Group](#api-group)
- [API Registry Model](#api-registry-model)
- [API Registry](#api-registry)
  - [API Groups](#api-groups)
    - [API Group `format`](#api-group-format)
  - [API Resources](#api-resources)
    - [API Version `format`](#api-version-format)
    - [API Document Representation](#api-document-representation)
    - [Validation Capabilities and Results](#validation-capabilities-and-results)
  - [API References and Operation Locators](#api-references-and-operation-locators)
    - [Locator Syntax and Encoding](#locator-syntax-and-encoding)
    - [Resolution Outcomes](#resolution-outcomes)
  - [API Formats](#api-formats)
    - [OpenAPI](#openapi)
    - [Swagger](#swagger)
    - [gRPC](#grpc)
    - [Apache Thrift](#apache-thrift)
    - [Apache Avro Protocol](#apache-avro-protocol)
    - [Apache Avro IDL](#apache-avro-idl)
    - [GraphQL](#graphql)
    - [WSDL](#wsdl)
    - [OpenRPC](#openrpc)
    - [Smithy](#smithy)
- [Example](#example)
- [Security Considerations](#security-considerations)
- [Conformance](#conformance)
- [References](#references)
  - [Normative References](#normative-references)
  - [Informative References](#informative-references)

## Overview

This extension applies to interfaces whose callers address operations and
receive correlated results, including HTTP APIs, gRPC services, SOAP services,
Thrift services, and JSON-RPC servers.

The registry does not translate API documents into a common operation model.
The native API document is authoritative for operation names, request and
response contracts, protocol bindings, security requirements, and other
format-specific metadata.

Request-response is the primary use case, not a restriction on every operation
in a stored document. Native descriptions can include streaming, one-way, and
callback operations. A resolver locates an operation in a registered
document. A Registry can store API documents without providing a resolver.
When reporting an operation, a resolver
MUST preserve its native exchange pattern. It MUST NOT report a one-way or
streaming operation as a unary request-response call.

Registration does not assert that a service is deployed or reachable. The
service's invocation addresses, where present, come from the native
description or separate deployment configuration, not from the registry's
`self` URL.

API Resources are xRegistry document Resources with `hasdocument: true` and
follow the [Core document and metadata rules][core]. The [Endpoint
Registry][endpoint] and [Message Registry][message] cover asynchronous delivery
and message contracts.

### API Documents and Schemas

API documents can define data shapes inline or reference documents in a
[Schema Registry][schema]. A registry server need not resolve such references
on write unless a validation check requires them.

Publishers MUST reference schemas that are compatible with the description
language's schema dialect. In particular, OpenAPI 3.0 and Swagger 2.0 Schema
Objects are not interchangeable with arbitrary JSON Schema documents. Storing
schemas in the same registry does not make their type systems interchangeable.

An API Version identifies an entry document, which the Registry can
[embed or reference](#api-document-representation). Dependencies use the
native language's `$ref`, import, include, or equivalent constructs.
Implementations MUST apply that language's base-URI and import rules. Unless
the native language establishes a base, the initial base for an embedded
document MUST be the canonical document URL of the selected Version: the
normal URL for retrieving that exact Version's document. It is not the
metadata `self` URL, a Resource's default-document or alias URL, or the URL
of a Registry JSON representation that embeds the document. For an external
document, the initial base is the effective retrieval URL after redirects.
If a needed relative reference has no applicable base, the check or
resolution MUST fail rather than guess.

Publishers MUST account for relative references when relocating documents.
Protobuf and Thrift include paths require explicit resolver configuration.
If that configuration is absent and the resolver cannot obtain a dependency
needed to identify the operation, it reports an unavailable dependency.
Namespace names and Smithy shape IDs are not retrieval URLs.

For reproducible resolution, publishers SHOULD reference explicit dependency
versions. An explicit API `versionid` does not freeze an externally hosted
document or its unversioned dependencies.

### Versioning

API Resources use the version and compatibility rules in [xRegistry Core][core].
When the server generates a `versionid`, API Registry implementations SHOULD
use Core's default generation algorithm.

This draft does not define format-specific API compatibility algorithms. An
implementation that declares support for a policy MUST document its comparison
rules, including the client/server direction, request acceptance, possible
responses and faults, and operation identity. Schema compatibility alone does
not establish API compatibility. An unsupported policy MUST NOT be reported as
successfully checked. Supported combinations of formats and policies are
announced through Core's capabilities, as described in
[Validation Capabilities and Results](#validation-capabilities-and-results).

## Notations and Terminology

### Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be
interpreted as described in BCP 14 ([RFC 2119][rfc2119] and
[RFC 8174][rfc8174]) when, and only when, they appear in all capitals.

In the pseudo-JSON snippets, `?` marks an OPTIONAL member, `*` marks zero or
more occurrences, and `+` marks one or more occurrences. Text after `#` is a
comment. Whitespace in these snippets is non-normative.

### Terminology

#### API

An API is a logical interface contract that defines one or more operations.
An API Resource represents this logical interface. An API Version identifies
a concrete API document, either embedded or externally hosted.

#### API Document

An API document is a native document in an API description language, such as
OpenAPI, Protocol Buffers, Thrift IDL, or WSDL. It declares operations and
their format-specific request, response, error, security, and transport data.

#### Operation

An operation is a callable interaction defined within an API document. Its
identifier and request and response contract are format-specific.

#### Operation Locator

An operation locator is the selector in an
[operation reference](#api-references-and-operation-locators). It identifies
one operation within the selected API document.

#### API Group

An API Group is a container for related API Resources. Deployments choose how
to group them. The Group can restrict the
[`format`](#api-group-format) of its API Versions.

## API Registry Model

The xRegistry extension model resides in [model.json](model.json).

The following pseudo-JSON omits Core attributes and collection metadata. A
representation can include at most one of the
[three document members](#api-document-representation). The example shows a
default Version with a format check result. See
[Validation Capabilities and Results](#validation-capabilities-and-results)
for the meaning of that result.

```yaml
{
  "apigroups": {
    "<KEY>": {
      "apigroupid": "<STRING>",
      # Core Group attributes
      ...
      "format": "<STRING>", ?

      "apis": {
        "<KEY>": {
          "apiid": "<STRING>",
          # Default Version attributes
          ...
          "format": "<STRING>",
          "formatvalidated": <BOOLEAN>,
          "formatvalidatedreason": "<STRING>", ?
          "compatibilityvalidated": <BOOLEAN>, ?
          "compatibilityvalidatedreason": "<STRING>", ?
          "apiurl": "<URL>", ?
          "api": <ANY>, ?
          "apibase64": "<STRING>", ?

          # Core Resource attributes and Versions collection
          ...
        } *
      } ?
    } *
  } ?
}
```

## API Registry

The API Registry uses the group, resource, version, document, compatibility,
and extension rules defined by [xRegistry Core][core].

### API Groups

The singular Group name is `apigroup`. The plural collection name is
`apigroups`. Every API Resource MUST belong to an API Group.

A group MAY contain documents in different formats when it has no `format`
attribute.

#### API Group `format`

- Type: String
- Description: An OPTIONAL format restriction for all API Resources in the
  group.
- Constraints:
  - OPTIONAL.
  - MUST be a non-empty format identifier when present.
  - When the group declares `format`, every API Version in the group MUST
    declare a matching `format` value, compared case-insensitively.

The following example restricts an API Group to OpenAPI 3.1 documents.

```json
{
  "apigroupid": "com.example.users",
  "format": "OpenAPI/3.1"
}
```

### API Resources

The singular Resource name is `api`. The plural collection name is `apis`.

API Resources use `maxversions: 0`, `setversionid: true`, `hasdocument: true`,
`validateformat: true`, `validatecompatibility: true`, and
`strictvalidation: false` in the working-draft model. Their semantics are
defined by [xRegistry Model][model].

#### API Version `format`

- Type: String
- Description: Identifies the API document language and, when specified, its
  version or profile.
- Constraints:
  - REQUIRED on every API Version.
  - MUST be a non-empty, case-insensitive string of the form
    `<SPEC>[/<VERSION>]`.
  - MUST identify the description language and, when specified, its language
    version or profile. This is distinct from `versionid` and the version of
    the described service. See [API Formats](#api-formats) for the complete
    identifiers of the profiles defined by this draft.
  - MUST match the API Group's `format` when the group declares one.
  - All Versions of an API Resource MUST use the same complete `format` value,
    compared case-insensitively. The API Registry MUST enforce this comparison
    independently of Core's `matchversions` aspect, which compares string
    values exactly, including case. The API Registry MUST reject a write that
    leaves a Version's `format` in conflict with its Group or another Version
    of its Resource. Thus `OpenAPI/3.0` and `OpenAPI/3.1` require separate
    Resources even if the described service contract is unchanged.

#### API Document Representation

Core derives the API document members `api`, `apiurl`, and `apibase64`. At most
one MAY appear in a representation. Core's [`typemap` rules][typemap]
determine the embedded form from `contenttype`. A valid document mapped to
`json` appears as a JSON value in `api`; one mapped to `string` appears as a
string in `api`. For example, `application/json` maps to `json`, and the API
[model](model.json) maps `application/yaml` and `application/x-yaml` to
`string`. Binary documents, including gRPC descriptor sets, use `apibase64`.
An `apiurl` identifies an externally hosted document, not the Resource `self`
URL or an API invocation address.

The server MUST retain the native document language. It MUST NOT
translate the document to another API description language. This does not add
a byte-for-byte preservation requirement beyond Core's serialization rules.

#### Validation Capabilities and Results

Servers advertise validation support through [Core's Registry
Capabilities][capabilities]. Match API `format` values against
[`capabilities.formats`][formatscapability] entries and
[`capabilities.compatibilities`][compatibilitiescapability] keys
case-insensitively, using Core's wildcard rules where applicable. The
`compatibilities` values list the case-insensitive rule names supported for
each format. Defining a profile in [API Formats](#api-formats) does not
mean a particular server supports validation for it.

For embedded documents in a supported format, `validateformat: true` requires
validation against the selected API profile, including the applicable
requirements of the native description language. Parsing JSON or XML alone
does not establish conformance. Malformed or invalid documents MUST be
rejected. Successful checks set `formatvalidated: true` under Core's result
rules. Any external retrieval needed to validate follows
[Security Considerations](#security-considerations).

With `strictvalidation: false`, unsupported formats and external documents can
be accepted without format checking. They use `formatvalidated: false` and
`formatvalidatedreason` as defined by Core. The value `false` records an
unchecked result, not that an invalid document was accepted.

When `meta.compatibility` is present, supported compatibility policies MUST be
checked under Core's rules. Violations MUST be rejected even with
`strictvalidation: false`. Skipped checks use `compatibilityvalidated: false`
and `compatibilityvalidatedreason`. Successful checks use `true` without a
reason. Without a compatibility policy, these result attributes MUST be absent.

If the server is REQUIRED to check a supported format or compatibility
policy but cannot finish because a dependency is unavailable, retrieval is
denied, or a retrieval limit is exceeded, the server MUST reject the write,
even when `strictvalidation` is `false`. The server MUST distinguish an
incomplete check from a detected format or compatibility violation. The
Core rules for an external Version document still apply; they do not waive
this obligation for a dependency of a check.

### API References and Operation Locators

An API Resource or Version reference identifies the API contract as a whole.
Other documents can use this specification's locators to identify a specific
operation, qualified by its containing interface or service where applicable.
This is similar to using [Schema Registry][schema] locators to identify
individual type definitions.

An operation reference combines a Core Resource or Version XID or absolute
URL with an operation locator. A Resource reference selects its default
Version. A Version reference selects an explicit Version, as shown in these
examples.

```text
/apigroups/users/apis/UserProfileService#operations/GetUserProfile
/apigroups/users/apis/UserProfileService/versions/2#operations/GetUserProfile
```

This composite reference is not a Core XID. `#` separates the entity reference
from the locator. Resolution requires an API-aware resolver. HTTP does not send
the fragment to the server.

For a document-view reference, the caller supplies the Registry JSON document
in which the resolver evaluates the JSON Pointer. The fragment does not
identify that document. The following example uses a colon to append an
operation locator to the document-local pointer.

```text
#/apigroups/users/apis/UserProfileService:operations/GetUserProfile
```

This extension reference is neither a fragment-based XID nor an ordinary
JSON Pointer. The resolver splits at the first literal `:` in the fragment.
Colons in the entity pointer's data MUST therefore be percent-encoded as
`%3A`. After splitting, the resolver interprets the portion before the
separator as the URI fragment representation of a JSON Pointer
([RFC 6901, Section 6][rfc6901]). It percent-decodes that portion once,
then evaluates the pointer in the supplied Registry JSON document. A
pointer to an API Resource selects its default Version. A pointer to an
API Version selects that exact Version. The selector after the separator
follows the encoding rules below.

For this reference form, the supplied Registry JSON is the sole authority
for Version identity, default selection, and `format`. The resolver MUST
fail if the pointer has no target or the supplied view lacks the information
needed to select the Version or determine its format. It MUST NOT retrieve
live metadata to complete the view or select another Version. If the
selected Version's document is not embedded, the resolver MAY obtain that
document through an explicit document locator, such as `apiurl`, subject to
retrieval policy. A missing target or missing metadata in the supplied view
does not establish that the entity is absent from the Registry.

The following example assumes the supplied Registry JSON document includes
Version `2` under the Resource's `versions` collection:

```text
#/apigroups/users/apis/UserProfileService/versions/2:operations/GetUserProfile
```

An operation locator selects content in that API document, never a nested
xRegistry operation Resource. This draft defines no `operations` collection.

#### Locator Syntax and Encoding

The following notation shows the supported selectors. Angle-bracketed names
are tokens.

```text
operations/<operation-name>
services/<service-name>/operations/<operation-name>
interfaces/<interface-name>/operations/<operation-name>
interfaces/<interface-name>/operations/<operation-name>/input/<input-name>/output/<output-name>
operations/<query|mutation|subscription>/<field-name>
/<JSON-Pointer-tokens>
```

Tokens MUST be non-empty, with exact, case-sensitive comparison unless a native
language explicitly specifies otherwise. Literal selector words are
case-sensitive. A leading `/` selects [RFC 6901][rfc6901] JSON Pointer syntax,
which is supported here only for OpenAPI and Swagger operation objects.

To encode a name token, replace `~` with `~0`, then `/` with `~1`. Join the
tokens with the `/` delimiters shown in the selector syntax. Apply
[RFC 3986][rfc3986] percent encoding to the selector's UTF-8 representation.
Literal `%`, `#`, braces, and spaces in names require encoding. For example,
Smithy's shape separator becomes `%23`, not a second literal `#`. For a JSON
Pointer selector, use the fragment encoding from [RFC 6901][rfc6901].

A resolver MUST separate the entity reference and selector before decoding.
It MUST percent-decode the selector exactly once, split it into tokens at `/`,
then reverse `~1` and `~0` escapes in that order. Invalid percent or tilde
escapes MUST fail. A JSON Pointer selector follows RFC 6901 after the single
percent-decoding step. Decoded slashes from `~1` MUST NOT be split again.

#### Resolution Outcomes

The resolver MUST first select one API Version and obtain its document and
format. If the caller names an explicit Version, the resolver MUST NOT
substitute the default or another Version. Dependency resolution follows
native language rules and the policy in
[Security Considerations](#security-considerations). The resolver succeeds
only when exactly one operation matches.

Resolvers MUST distinguish malformed references, unsupported formats,
unavailable documents or dependencies, policy-denied retrievals, absent
operations, and ambiguous matches. They MUST NOT choose the first candidate
or return success after a dependency needed to identify the operation failed.
This draft does not assign HTTP status codes to local resolution outcomes or
introduce a server-side locator endpoint.

### API Formats

The following profiles define complete registry `format` identifiers and
operation selectors. A profile that specifies a suffix uses it as part of the
identifier. This draft also defines the unqualified identifier `Thrift`.
Implementations MAY support additional profiles. Resolvers MUST report unknown
profiles as unsupported rather than infer their syntax.

Format-specific operation locators use the shared
[syntax and encoding rules](#locator-syntax-and-encoding) and
[resolution outcomes](#resolution-outcomes).

#### OpenAPI

`OpenAPI` is the `<SPEC>` component of the `format` identifier. The suffix
identifies the OpenAPI Specification feature set that defines the API.

- `OpenAPI/3.0` selects `3.0.*` as defined by [OpenAPI 3.0.4][oas30].
- `OpenAPI/3.1` selects `3.1.*` as defined by [OpenAPI 3.1.1][oas31].

The API document is an OpenAPI Description in JSON or YAML. The root `openapi`
field MUST match the selected feature set. It is independent of `info.version`.
JSON and YAML representations MUST be distinguished by `contenttype`.
For example, `application/json` selects the JSON representation, while
`application/yaml` selects YAML text under the model's
[document representation](#api-document-representation) rules.

For OpenAPI, `operations/<operationId>` resolves an Operation
Object with that `operationId` in the API that the entry document describes,
including referenced path items and operations. Publishers SHOULD supply
`operationId`. When present, it MUST be unique as specified by the native
specification. An ambiguous match MUST fail.

A reference to an operation without an `operationId` MUST use a JSON
Pointer to the Operation Object in the entry document. The following
reference uses an explicit API Version and a JSON Pointer fragment:

```text
/apigroups/users/apis/UserProfileService/versions/2#/paths/~1users~1%7BuserId%7D/get
```

The fragment selects `paths["/users/{userId}"].get` in the parsed entry
document. An operation in a separate document without an `operationId`
cannot be addressed through that entry document. JSON Pointer evaluation
does not traverse `$ref`. A pointer MUST target an Operation Object.
Pointing at a Reference Object does not
select the referenced operation. A resolver can select externally defined
operations by their operation ID through the resolved API. If the external
document is itself registered as a conforming API document, a resolver can use
a pointer with that document's own API Resource or Version reference.

#### Swagger

The `<SPEC>` component for Swagger is `Swagger`. `Swagger/2.0` identifies a
[Swagger 2.0 document][swagger] in JSON or YAML. The root `swagger` value MUST
be `2.0`, independent of `info.version`. JSON and YAML representations MUST be
distinguished by `contenttype`, as for [OpenAPI](#openapi).

Swagger uses the same operation-ID and JSON Pointer locator rules as
[OpenAPI](#openapi), including uniqueness, reference resolution, and the
requirement that a pointer target an Operation Object.

#### gRPC

The `<SPEC>` component for gRPC is `gRPC`. Its profiles identify the
description representation, not a gRPC wire protocol version.

- `gRPC/proto3` identifies [Proto3][proto3] source.
- `gRPC/descriptor-set` identifies a binary [FileDescriptorSet][descriptor].

`gRPC/proto3` requires `syntax = "proto3"` source with at least one service
declaration. Proto2 and Editions source documents require additional published
profiles.

`gRPC/descriptor-set` requires a serialized `google.protobuf.FileDescriptorSet`
with at least one service descriptor. Descriptor dependencies needed for
resolution MUST be included or supplied by an explicitly configured resolver.
Descriptor validation MUST account for each file's syntax or edition.
Even if a file declares an unrecognized edition, the validator MUST check
all files with recognized syntax or editions to the extent those checks can
be performed independently of the unrecognized edition. If the validator
finds a malformed descriptor set or a violation of recognized rules, the
server MUST reject the write.

A check blocked solely by an unrecognized edition, including a check that
depends on a file of that edition, is not a failed dependency retrieval.
The server MUST NOT report successful validation for an unrecognized
edition. If the unrecognized edition is the only reason validation could
not be completed, a server with `strictvalidation: false` MAY accept the
document as unchecked. If it accepts the document, it MUST set
`formatvalidated` to `false` and explain the reason in
`formatvalidatedreason`. A server with `strictvalidation: true` MUST reject
the write if it cannot check the declared edition.

Binary descriptors use `apibase64` in an embedded JSON representation, not
a JSON rendering of the descriptor messages.

For gRPC, a locator identifies a service and a remote procedure call (RPC)
method, as shown in the following example.

```text
#services/com.example.users.UserProfileService/operations/GetUserProfile
```

The service token MUST be its Protobuf package followed by `.` and the service
name, without a leading dot. Without a package, it is the service name alone.
Descriptor-set service names MUST resolve uniquely across the set. The method
token is its case-sensitive RPC name. Request and response types and
client/server streaming flags come from the selected method declaration.

#### Apache Thrift

The `format` identifier for Apache Thrift is `Thrift`. The API document is
text conforming to the [Thrift IDL grammar][thrift], which has no document-level
language-version field. A validator MUST identify the compiler or grammar
revision it supports. Thrift target-language namespaces do not define a
universal service namespace.

For Thrift, the service token is the service identifier declared in the entry
IDL document, not a namespace chosen for generated Java, Python, or other code.
The following locator identifies an operation in that service.

```text
#services/UserProfileService/operations/GetUserProfile
```

A resolver selects the method from that service after resolving its `extends`
chain. Inherited methods are selectable. Ambiguous declarations MUST fail. A
service declared only in an included IDL document requires a reference to
that document's own API Resource or an explicit Version of that Resource.
The registry does not invent a target-language namespace for included
services. `oneway` and declared exceptions retain their native meaning.

#### Apache Avro Protocol

The `<SPEC>` component for Apache Avro Protocol is `AvroProtocol`. The suffix
identifies the Apache Avro release used to define the protocol.
`AvroProtocol/1.12.0` identifies a JSON document conforming to the
[Avro 1.12.0 protocol rules][avro]. The document MUST contain a protocol
declaration. Avro data schemas are outside this API profile.

The following locator uses the name of a message in the protocol's `messages`
member.

```text
#operations/GetUserProfile
```

The protocol is authoritative for the request, response, errors, and one-way
flag.

#### Apache Avro IDL

The `<SPEC>` component for Apache Avro IDL is `AvroIDL`. The suffix identifies
the Apache Avro release used to define the IDL. `AvroIDL/1.12.0` identifies text
conforming to the [Avro 1.12.0 IDL rules][avroidl]. The IDL MUST produce a
protocol, not only a data schema. Schema-only IDL is outside this API profile.

The following locator uses the message name in the resolved protocol.

```text
#operations/GetUserProfile
```

Imported protocol messages participate in operation resolution after native
import processing. The resolved protocol is authoritative for the request,
response, errors, and one-way flag.

#### GraphQL

The `<SPEC>` components for GraphQL are `GraphQL` for schema definition
language (SDL) text and `GraphQLIntrospection` for introspection JSON. The
version identifies the GraphQL specification edition:

- `GraphQL/September2025` identifies SDL conforming to
  [GraphQL September 2025][graphql].
- `GraphQLIntrospection/September2025` identifies a complete introspection
  response for that edition.

GraphQL SDL MUST define a valid schema under the September 2025 specification.
For this draft's introspection profile, the document MUST be a JSON response
object with `data.__schema` and no `errors`. It MUST describe all root operation
types and named types, including deprecated fields, enum values, arguments,
and input fields. Type references MUST include the full `kind`, `name`, and
`ofType` chains. Descriptions can be omitted. Missing information needed to
reconstruct the schema makes the representation incomplete and MUST cause
validation or operation resolution to fail. The types and fields listed above
are not by themselves a completeness test: reconstruction also needs schema
information such as directives and default values where they apply. A partial
introspection query result is not a complete schema document.

The publisher supplies a complete introspection result for the schema it
describes. A validator reading only the stored response can check
reconstruction from the data supplied; it cannot tell from that response
alone whether the publisher omitted a type that existed in the original
schema.

For GraphQL, the following locators identify the root operation type and its
field.

```text
#operations/query/userProfile
#operations/mutation/updateUserProfile
```

The operation kind MUST be `query`, `mutation`, or `subscription`. The field
MUST exist on the corresponding root type identified by the schema definition
or introspection data. That type need not be named `Query` or `Mutation`. The
locator identifies a root schema field, not a named executable GraphQL
operation or a complete selection set. A subscription retains its streaming
semantics.

#### WSDL

The `<SPEC>` component for WSDL is `WSDL`. The suffix identifies the WSDL
specification that defines the XML document.

- `WSDL/1.1` identifies [WSDL 1.1][wsdl11].
- `WSDL/2.0` identifies [WSDL 2.0 Part 1][wsdl20].

WSDL versions are identified by their document element and WSDL namespace:
`definitions` in `http://schemas.xmlsoap.org/wsdl/` for 1.1 and `description` in
`http://www.w3.org/ns/wsdl` for 2.0. Bindings and message exchange patterns
remain native WSDL constructs.

For WSDL, an interface token MUST use the expanded QName `{namespace}local`,
independent of XML prefix choices. Apply token escaping and percent encoding
to the entire expanded name. The following example selects an operation in a
WSDL 1.1 port type in `urn:example:users`.

```text
#interfaces/%7Burn:example:users%7DUserProfilePortType/operations/GetUserProfile
```

WSDL 1.1 uses the operation's local name. A name-only selector MUST fail if
more than one operation has that local name in the selected port type.
An overload can be selected using both effective input and output names,
including the defaults specified by WSDL 1.1 section 2.4.5. Use the token
`!` for an absent input or output. The token `!` is not a valid XML NMTOKEN.
WSDL 1.1 input and output names are NMTOKENs, not NCNames.
The following locator selects an overload by its input and output names.

```text
#interfaces/%7Burn:example:users%7DUserProfilePortType/operations/GetUserProfile/input/GetUserProfileRequest/output/GetUserProfileResponse
```

For WSDL 2.0, both the interface and operation tokens MUST be expanded QNames.
An inherited operation retains its declaring namespace. Equivalent inherited
components with the same QName identify one operation. Conflicting components
make the document invalid under WSDL's component rules. The input and output
overload suffix is only defined for WSDL 1.1. No WSDL operation locator chooses
a service endpoint or binding. Those are separate native WSDL components.

#### OpenRPC

The `<SPEC>` component for OpenRPC is `OpenRPC`. `OpenRPC/1.4` identifies an
[OpenRPC 1.4][openrpc14] JSON document whose root `openrpc` value is `1.4.*`,
independent of `info.version`. The profile refers to the released 1.4
specification, not a later edition on the publisher's live site.

The following locator uses the method name.

```text
#operations/GetUserProfile
```

The token MUST match the `name` of exactly one resolved Method Object in
`methods`. Parameters, result, and errors come from that object, not from an
example JSON-RPC request.

#### Smithy

The `<SPEC>` component for Smithy is `Smithy`. `Smithy/2.0` identifies a Smithy
2 model in [IDL][smithyidl] or [JSON AST][smithyast] form. AST stands for
abstract syntax tree.

Smithy uses IDL `$version` or the AST `smithy` field. Values `2` and `2.0`
select the Smithy 2 model. `contenttype` MUST distinguish IDL text from JSON
AST. For example, the model maps `application/smithy` to `string`, while Core
maps `application/json` to `json`. The model MUST include an operation shape.
Resolving a shape MUST NOT infer a deployment address or protocol binding
that the model does not supply.

For Smithy, the token is the absolute operation shape ID, as shown in the
following example.

```text
#operations/com.example.users%23GetUserProfile
```

The ID MUST resolve to an operation shape in the assembled model, not a service,
resource, or data shape. Assembly MUST resolve the model files needed for
that operation. Input, output, errors, and traits retain their Smithy meaning.

## Example

This abbreviated xRegistry 1.0-rc4 response shows the API-specific fields for
an OpenAPI 3.1 document. It omits Core metadata and collection fields. The
server does not support OpenAPI validation, so `formatvalidated: false`
records a skipped check.

```jsonc
{
  "specversion": "1.0-rc4",
  "registryid": "example-registry",
  "apigroups": {
    "com.example.users": {
      "apigroupid": "com.example.users",
      "format": "OpenAPI/3.1",
      "apis": {
        "UserProfileService.v1": {
          "apiid": "UserProfileService.v1",
          "versionid": "1",
          "contenttype": "application/json",
          "format": "OpenAPI/3.1",
          "formatvalidated": false,
          "formatvalidatedreason": "OpenAPI/3.1 validation is not supported by this registry",
          "api": {
            "openapi": "3.1.0",
            "info": {
              "title": "User Profile Service",
              "version": "1.0.0"
            },
            "paths": {
              "/users/current": {
                "get": {
                  "operationId": "GetUserProfile",
                  "responses": {
                    "200": { "description": "The user profile" },
                    "404": { "description": "No matching user" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

The following reference identifies the `GetUserProfile` operation in this
example.

```text
/apigroups/com.example.users/apis/UserProfileService.v1#operations/GetUserProfile
```

## Security Considerations

Documents, operation names, and dependency links are untrusted input. Registry
write access does not grant permission to contact the described API. Resolvers
MUST NOT invoke operations while validating or resolving a description.

An implementation that retrieves an external document MUST obtain explicit
policy authorization, including for each redirect target. Storing a reference
does not authorize retrieval. When resolving operations or retrieving
external documents or dependencies for validation, implementations MUST
enforce limits on document size, retrieval count, recursion depth, and
duration, and detect dependency cycles. If a cycle
or limit prevents resolution of a dependency needed to identify the operation,
the resolver MUST report failure. Local file access and private network access
MUST be denied unless explicitly authorized.
Credentials MUST NOT be forwarded automatically across origins. XML parsers
MUST disable external-entity expansion. YAML parsers MUST NOT construct native
objects from document tags. These are requirements of this working-draft
extension, not additional claims about the cited description languages.

Registry authentication and authorization are separate from the API's security
requirements. API documents SHOULD describe security schemes without embedding
passwords, access tokens, or private keys. Consumers MUST apply their own trust
policy to servers and authorization URLs found in a document.

## Conformance

A registry implementing this extension MUST implement the group and resource
model and the applicable Core document, metadata, and validation rules. It is
not REQUIRED to implement every language parser or an operation resolver. A
resolver that declares support for a profile MUST implement that profile's
identity, escaping, dependency, and failure rules. Storage support alone is not
locator support.

The [API model](model.json) validates against the
[model JSON Schema][modelschema] at the pinned Core 1.0-rc4 revision.
Schema validation checks the model's structure, not whether a registry
implements Core or this extension correctly.

The referenced language standards remain authoritative for API document
contents. This extension defines the Registry model, document handling and
validation rules, and operation selection, not the semantics of the native
API documents.

## References

### Normative References

- [xRegistry Core][core] and [xRegistry Model][model], including the Core
  [model JSON Schema][modelschema].
- [RFC 2119][rfc2119] and [RFC 8174][rfc8174], BCP 14 requirement terminology.
- [RFC 3986][rfc3986], URI syntax, percent encoding, and reference resolution.
- [RFC 6901][rfc6901], JSON Pointer evaluation and URI fragment representation.
- [OpenAPI 3.0.4][oas30], [OpenAPI 3.1.1][oas31], and [Swagger 2.0][swagger].
- [Protocol Buffers proto3 language specification][proto3] and
  [FileDescriptorSet schema][descriptor], unversioned publisher sources.
- [Apache Thrift IDL][thrift], unversioned publisher language reference.
- [Apache Avro 1.12.0 specification][avro] and [IDL reference][avroidl].
- [GraphQL September 2025][graphql], type system, introspection, and responses.
- [WSDL 1.1][wsdl11] and [WSDL 2.0 Part 1][wsdl20].
- [OpenRPC 1.4][openrpc14], released specification source.
- [Smithy 2.0 IDL][smithyidl], [JSON AST][smithyast], and
  [model specification][smithymodel], publisher's maintained 2.0 references.

### Informative References

- [xRegistry Schema Registry][schema], document-store and deep-reference precedent.
- [xRegistry Endpoint Registry][endpoint] and [Message Registry][message],
  asynchronous delivery and message definitions.
- [OpenRPC specification site][openrpc], the publisher's live page.
- [JSON-RPC 2.0][jsonrpc], wire protocol described by OpenRPC.

[core]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/spec.md
[capabilities]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/spec.md#registry-capabilities
[formatscapability]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/spec.md#formats-capability
[compatibilitiescapability]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/spec.md#compatibilities-capability
[model]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/model.md
[typemap]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/model.md#groupsstringresourcesstringtypemap
[modelschema]: https://github.com/xregistry/spec/blob/3aac648d34cd022cdd752c3c5782312404aca48d/core/model.schema.json
[schema]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/schema/spec.md
[endpoint]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/endpoint/spec.md
[message]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/message/spec.md
[rfc2119]: https://www.rfc-editor.org/rfc/rfc2119
[rfc8174]: https://www.rfc-editor.org/rfc/rfc8174
[rfc3986]: https://www.rfc-editor.org/rfc/rfc3986
[rfc6901]: https://www.rfc-editor.org/rfc/rfc6901
[oas30]: https://spec.openapis.org/oas/v3.0.4.html
[oas31]: https://spec.openapis.org/oas/v3.1.1.html
[swagger]: https://spec.openapis.org/oas/v2.0.html
[proto3]: https://protobuf.dev/reference/protobuf/proto3-spec/
[descriptor]: https://raw.githubusercontent.com/protocolbuffers/protobuf/main/src/google/protobuf/descriptor.proto
[thrift]: https://thrift.apache.org/docs/idl
[avro]: https://avro.apache.org/docs/1.12.0/specification/
[avroidl]: https://avro.apache.org/docs/1.12.0/idl-language/
[graphql]: https://spec.graphql.org/September2025/
[wsdl11]: https://www.w3.org/TR/2001/NOTE-wsdl-20010315
[wsdl20]: https://www.w3.org/TR/2007/REC-wsdl20-20070626/
[openrpc]: https://spec.open-rpc.org/
[openrpc14]: https://github.com/open-rpc/spec/blob/3a13c7a8bad248e6edd2d48339cd1c06b57f8f22/spec/1.4/spec-template.md
[jsonrpc]: https://www.jsonrpc.org/specification
[smithyidl]: https://smithy.io/2.0/spec/idl.html
[smithyast]: https://smithy.io/2.0/spec/json-ast.html
[smithymodel]: https://smithy.io/2.0/spec/model.html
