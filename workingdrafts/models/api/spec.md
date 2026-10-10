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
<!-- words: validateformat wsdl xmlsoap -->

## Abstract

This document defines an API Registry extension to the xRegistry
document format and API. An API Registry stores and manages versioned API
definition documents for synchronous request-response interfaces.

This working draft is dated 15 September 2026 and is not part of a released
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
receive correlated results, including HTTP APIs, gRPC and SOAP services,
Thrift services, and JSON-RPC servers.

The registry does not translate API documents into a common operation model.
The native API document is authoritative for operation names, request and
response contracts, protocol bindings, security requirements, and other
format-specific metadata.

Request-response is the primary use case, not a restriction on every operation
in a stored document. Native descriptions can include streaming, one-way, and
callback operations. Resolvers MUST preserve those exchange patterns and MUST
NOT report a one-way or streaming operation as a unary request-response call.
Registration does not assert that a service is deployed or reachable. Its
invocation addresses, where present, come from the native description or from
separate deployment configuration, not from the registry's `self` URL.

API Resources are xRegistry document Resources with `hasdocument: true` and
follow the [Core document and metadata rules][core]. The [Endpoint
Registry][endpoint] and [Message Registry][message] cover asynchronous delivery
and message contracts.

### API Documents and Schemas

API documents can define data shapes inline or reference documents in a
[Schema Registry][schema]. A registry server does not need to resolve such
references to store the API document.

Referenced schemas MUST be compatible with the description language's schema
dialect. In particular, OpenAPI 3.0 and Swagger 2.0 Schema Objects are not
interchangeable with arbitrary JSON Schema documents. Storing schemas in the
same registry does not make their type systems interchangeable.

An API Version identifies an entry document. Dependencies use the native
language's `$ref`, import, include, or equivalent constructs. Resolvers MUST
apply that language's base-URI and import rules. The initial base is the
document retrieval URL for an embedded document and the effective retrieval
URL after redirects for an external document, unless a native identifier
establishes another base. Publishers MUST account for relative references when
relocating documents. Protobuf and Thrift include paths require explicit
resolver configuration; namespace names and Smithy shape IDs are not retrieval
URLs.

For reproducible resolution, publishers SHOULD reference explicit dependency
versions. An explicit API `versionid` does not freeze an externally hosted
document or its unversioned dependencies.

### Versioning

API Resources use the version and compatibility rules in [xRegistry Core][core].
When the server generates a `versionid`, API Registry implementations SHOULD
use Core's default generation algorithm.

This draft does not define format-specific API compatibility algorithms. An
implementation claiming support for a policy MUST document its comparison
rules, including the client/server direction, request acceptance, possible
responses and faults, and operation identity. Schema compatibility alone does
not establish API compatibility. An unsupported policy MUST NOT be reported as
successfully checked. Supported format/policy combinations are announced through
Core's capabilities, as described in
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

An API is a logical interface contract comprising one or more operations. An
API Resource represents this logical interface; an API Version stores a
concrete API document.

#### API Document

An API document is a native document in an API description language, such as
OpenAPI, Protocol Buffers, Thrift IDL, or WSDL. It declares operations and
their format-specific request, response, error, security, and transport data.

#### Operation

An operation is a callable interaction defined within an API document. Its
identifier and request and response contract are format-specific.

#### Operation Locator

An operation locator is a fragment appended to an API Resource reference. It
identifies one operation within the selected API document version.

#### API Group

An API Group is a container for related API Resources. This specification does
not constrain how resources are grouped.

## API Registry Model

The xRegistry extension model resides in [model.json](model.json).

The following pseudo-JSON omits Core attributes and collection metadata. The
three document members are alternatives, not independent OPTIONAL values.

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

The singular Group name is `apigroup`; the plural collection name is
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

Example:

```json
{
  "apigroupid": "com.example.users",
  "format": "OpenAPI/3.1"
}
```

### API Resources

The singular Resource name is `api`; the plural collection name is `apis`.

API Resources use `maxversions: 0`, `setversionid: true`, `hasdocument: true`,
`validateformat: true`, `validatecompatibility: true`, and
`strictvalidation: false` in the working-draft model. Their semantics are
defined by [xRegistry Model][model].

#### API Version `format`

- Type: String
- Description: Identifies the API document language and its version.
- Constraints:
  - REQUIRED on every API Version.
  - MUST be a non-empty, case-insensitive string of the form
    `<SPEC>[/<VERSION>]`.
  - MUST identify the description language and, when specified, its language
    version or profile. This is distinct from `versionid` and the version of
    the described service.
  - MUST match the API Group's `format` when the group declares one.
  - All Versions of an API Resource MUST use the same complete `format` value,
    compared case-insensitively, because the model sets `matchversions: true`.
    Thus `OpenAPI/3.0` and `OpenAPI/3.1` require separate Resources even if the
    described service contract is unchanged.

#### API Document Representation

Core derives the API document members `api`, `apiurl`, and `apibase64`; at most
one MAY appear in a representation. Textual API media types map to Core's
`string` representation and can appear in `api`. Binary documents, including
gRPC descriptor sets, use `apibase64`. An `apiurl` identifies an externally
hosted document, not the Resource `self` URL or an API invocation address.

The server MUST retain the native document language. It MUST NOT silently
translate the document to another API description language. This does not add
a byte-for-byte preservation requirement beyond Core's serialization rules.

#### Validation Capabilities and Results

Servers advertise validation support through [Core's Registry
Capabilities][capabilities]. `capabilities.formats` uses the API `format` values
defined below, and `capabilities.compatibilities` maps them to supported
compatibility rules. A format listed in this specification is not necessarily
supported by an implementation.

For embedded documents in a supported format, `validateformat: true` requires
validation against the selected API profile. Parsing JSON or XML alone does
not establish conformance. Malformed or invalid documents MUST be rejected;
successful checks set `formatvalidated: true` under Core's result rules.

With `strictvalidation: false`, unsupported formats and external documents can
be accepted without format checking. They use `formatvalidated: false` and
`formatvalidatedreason` as defined by Core; `false` means not checked, not
invalid-but-accepted.

When `meta.compatibility` is present, supported compatibility policies MUST be
checked under Core's rules. Violations MUST be rejected even with
`strictvalidation: false`. Skipped checks use `compatibilityvalidated: false`
and `compatibilityvalidatedreason`; successful checks use `true` without a
reason. Without a compatibility policy, these result attributes MUST be absent.

### API References and Operation Locators

An API Resource or Version reference identifies the API contract as a whole.
Other documents often need to reference a specific interface or operation, so
this specification also defines deep-reference locators for those elements,
similar to the [Schema Registry][schema] locators for individual type
definitions. These locators can also be used wherever a consumer needs to
identify part of an API precisely.

An API reference combines a Core Resource or Version XID or absolute URL with
an operation locator. A Resource reference selects its default Version; a
Version reference is explicit:

```text
/apigroups/users/apis/UserProfileService#operations/GetUserProfile
/apigroups/users/apis/UserProfileService/versions/2#operations/GetUserProfile
```

This composite reference is not a Core XID. `#` separates the entity reference
from the locator. Resolution requires an API-aware resolver; HTTP does not send
the fragment to the server.

For a document-view reference that already uses a JSON Pointer fragment, this
extension defines a colon-suffix convention:

```text
#/apigroups/users/apis/UserProfileService:operations/GetUserProfile
```

This is an extension reference, not a fragment-based XID and not one ordinary
JSON Pointer. The resolver splits at the first literal `:` in the fragment;
colons in identifier data MUST therefore be percent-encoded as `%3A`. It then
evaluates the entity pointer in the registry document and obtains that entity's
API document. An explicit document-view Version reference is:

```text
#/apigroups/users/apis/UserProfileService/versions/2:operations/GetUserProfile
```

An operation locator selects content in that API document, never a nested
xRegistry operation Resource. This draft defines no `operations` collection.

#### Locator Syntax and Encoding

The supported selectors are shown below. Angle-bracketed names are tokens.

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

To encode a name token, replace `~` with `~0`, then `/` with `~1`. Construct the
selector from these tokens and percent-encode its UTF-8 representation as
specified by [RFC 3986][rfc3986]. In particular, literal `#`, braces, and spaces
in names require encoding. For example, Smithy's shape separator becomes
`%23`, not a second literal `#`.

A resolver MUST separate the entity reference and selector before decoding.
It MUST percent-decode the selector exactly once, split it into tokens at `/`,
then reverse `~1` and `~0` escapes in that order. Invalid percent or tilde
escapes MUST fail. A JSON Pointer selector follows RFC 6901 after the single
percent-decoding step. Decoded slashes from `~1` MUST NOT be split again.

#### Resolution Outcomes

The resolver MUST first select one API Version and obtain its document and
format. An explicit Version MUST NOT silently fall back to the default.
Dependency resolution follows native language rules and the security policy
below. The selected operation MUST exist and match exactly once.

Resolvers MUST distinguish malformed references, unsupported formats,
unavailable documents or dependencies, policy-denied retrievals, absent
operations, and ambiguous matches. They MUST NOT choose the first candidate
or return success after a dependency needed to identify the operation failed.
This draft does not assign HTTP status codes to local resolution outcomes or
introduce a server-side locator endpoint.

### API Formats

The following profiles define registry `format` identifiers and operation
selectors. Implementations MAY support additional profiles. Resolvers MUST
report unknown profiles as unsupported rather than infer their syntax.

Format-specific operation locators use the shared
[syntax and encoding rules](#locator-syntax-and-encoding) and
[resolution outcomes](#resolution-outcomes).

#### OpenAPI

The `format` identifier for OpenAPI is `OpenAPI`. The version identifies the
OpenAPI Specification feature set used to define the API:

- `OpenAPI/3.0` selects `3.0.*` as defined by [OpenAPI 3.0.4][oas30].
- `OpenAPI/3.1` selects `3.1.*` as defined by [OpenAPI 3.1.1][oas31].

The API document is an OpenAPI Description in JSON or YAML. The root `openapi`
field MUST match the selected feature set; it is independent of `info.version`.
JSON and YAML representations MUST be distinguished by `contenttype`.

For OpenAPI, `operations/{operationId}` resolves an Operation
Object with that `operationId` in the API described by the entry document,
including referenced path items and operations. Publishers SHOULD supply
`operationId`; when present it MUST be unique as specified by the native
specification. An ambiguous match MUST fail.

If an operation has no `operationId`, its reference MUST use a JSON Pointer to
the operation object:

```text
#/paths/~1users~1%7BuserId%7D/get
```

The preceding pointer selects `paths["/users/{userId}"].get` in the parsed
entry document. JSON Pointer evaluation does not traverse `$ref`. A pointer
MUST target an Operation Object; pointing at a Reference Object does not
select the referenced operation. Externally defined operations can be selected
by their operation ID through the resolved API, or by a pointer on the external
document's own retrieval reference where that document is registered as an API.

#### Swagger

The `format` identifier for Swagger is `Swagger`. `Swagger/2.0` identifies a
[Swagger 2.0 document][swagger] in JSON or YAML. The root `swagger` value MUST
be `2.0`, independent of `info.version`. JSON and YAML representations MUST be
distinguished by `contenttype`.

Swagger uses the same operation-ID and JSON Pointer locator rules as
[OpenAPI](#openapi), including uniqueness, reference resolution, and the
requirement that a pointer target an Operation Object.

#### gRPC

The `format` identifier for gRPC is `gRPC`. Its profiles identify the
description representation, not a gRPC wire protocol version:

- `gRPC/proto3` identifies [Proto3][proto3] source.
- `gRPC/descriptor-set` identifies a binary [FileDescriptorSet][descriptor].

`gRPC/proto3` requires `syntax = "proto3"` source with at least one service
declaration. Proto2 and Editions source documents require additional published
profiles.

`gRPC/descriptor-set` requires a serialized `google.protobuf.FileDescriptorSet`
with at least one service descriptor. Descriptor dependencies needed for
resolution MUST be included or supplied by an explicitly configured resolver.
Descriptor validation MUST account for each file's syntax or edition;
unrecognized editions MUST NOT be treated as checked. Binary descriptors use
`apibase64` in an embedded JSON representation, not a JSON rendering of the
descriptor messages.

For gRPC, a locator identifies a service and an RPC method:

```text
#services/com.example.users.UserProfileService/operations/GetUserProfile
```

The service token MUST be its protobuf package followed by `.` and the service
name, without a leading dot. Without a package it is the service name alone.
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
IDL document, not a namespace chosen for generated Java, Python, or other code:

```text
#services/UserProfileService/operations/GetUserProfile
```

The method is selected from that service after resolving its `extends` chain.
Inherited methods are selectable; ambiguous declarations MUST fail. A service
declared only in an included IDL document requires a reference to that
document's own API Resource. The registry does not invent a target-language
namespace for included services. `oneway` and declared exceptions retain their
native meaning.

#### Apache Avro Protocol

The `format` identifier for Apache Avro Protocol is `AvroProtocol`. The version
identifies the Apache Avro release used to define the protocol.
`AvroProtocol/1.12.0` identifies a JSON document conforming to the
[Avro 1.12.0 protocol rules][avro]. The document MUST contain a protocol
declaration; Avro data schemas are outside this API profile.

The locator uses a `messages` member name:

```text
#operations/GetUserProfile
```

The request, response, errors, and one-way flag remain authoritative in that
protocol.

#### Apache Avro IDL

The `format` identifier for Apache Avro IDL is `AvroIDL`. The version identifies
the Apache Avro release used to define the IDL. `AvroIDL/1.12.0` identifies text
conforming to the [Avro 1.12.0 IDL rules][avroidl]. The IDL MUST produce a
protocol, not only a data schema. Schema-only IDL is outside this API profile.

The locator uses the message name in the resolved protocol:

```text
#operations/GetUserProfile
```

Imported protocol messages participate in operation resolution after native
import processing. The request, response, errors, and one-way flag remain
authoritative in the resolved protocol.

#### GraphQL

The `format` identifiers for GraphQL are `GraphQL` for schema definition
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
validation or operation resolution to fail; a partial introspection query
result is not a complete schema document.

For GraphQL, the locator identifies the root operation type and its field:

```text
#operations/query/userProfile
#operations/mutation/updateUserProfile
```

The operation kind MUST be `query`, `mutation`, or `subscription`. The field
MUST exist on the corresponding root type identified by the schema definition
or introspection data; that type need not be named `Query` or `Mutation`. The
locator identifies a root schema field, not a named executable GraphQL
operation or a complete selection set. A subscription retains its streaming
semantics.

#### WSDL

The `format` identifier for WSDL is `WSDL`. The version identifies the WSDL
specification used to define the XML document:

- `WSDL/1.1` identifies [WSDL 1.1][wsdl11].
- `WSDL/2.0` identifies [WSDL 2.0 Part 1][wsdl20].

WSDL versions are identified by their document element and WSDL namespace:
`definitions` in `http://schemas.xmlsoap.org/wsdl/` for 1.1 and `description` in
`http://www.w3.org/ns/wsdl` for 2.0. Bindings and message exchange patterns
remain native WSDL constructs.

For WSDL, an interface token MUST use the expanded QName `{namespace}local`,
independent of XML prefix choices. Apply token escaping and percent encoding
to the entire expanded name. For a WSDL 1.1 port type in `urn:example:users`:

```text
#interfaces/%7Burn:example:users%7DUserProfilePortType/operations/GetUserProfile
```

WSDL 1.1 uses the operation's local name. A name-only selector MUST fail if
operations are overloaded. An overload can be selected using both effective
input and output names, including the defaults specified by WSDL 1.1 section
2.4.5. Use the token `!` for an absent input or output; `!` is not a valid XML
NMTOKEN. WSDL 1.1 input and output names are NMTOKENs, not NCNames.

```text
#interfaces/%7Burn:example:users%7DUserProfilePortType/operations/GetUserProfile/input/GetUserProfileRequest/output/GetUserProfileResponse
```

For WSDL 2.0, both the interface and operation tokens MUST be expanded QNames.
An inherited operation retains its declaring namespace. Equivalent inherited
components with the same QName identify one operation; conflicting components
make the document invalid under WSDL's component rules. The input/output
overload suffix is only defined for WSDL 1.1. Neither form chooses a service
endpoint or binding; those are separate native WSDL components.

#### OpenRPC

The `format` identifier for OpenRPC is `OpenRPC`. `OpenRPC/1.4` identifies an
[OpenRPC][openrpc] JSON document whose root `openrpc` value is `1.4.*`,
independent of `info.version`.

The locator uses the method name:

```text
#operations/GetUserProfile
```

The token MUST match the `name` of exactly one resolved Method Object in
`methods`. Parameters, result, and errors come from that object, not from an
example JSON-RPC request.

#### Smithy

The `format` identifier for Smithy is `Smithy`. `Smithy/2.0` identifies a Smithy
2 model in [IDL][smithyidl] or [JSON AST][smithyast] form.

Smithy uses IDL `$version` or the AST `smithy` field. Values `2` and `2.0`
select the Smithy 2 model. `contenttype` MUST distinguish IDL text from JSON
AST. The model MUST include an operation shape; resolving a shape MUST NOT
infer a deployment address or protocol binding that the model does not supply.

For Smithy, the token is the absolute operation shape ID:

```text
#operations/com.example.users%23GetUserProfile
```

The ID MUST resolve to an operation shape in the assembled model, not a service,
resource, or data shape. Assembly MUST resolve the model files needed for
that operation. Input, output, errors, and traits retain their Smithy meaning.

## Example

This abbreviated registry shows the API-specific fields for an OpenAPI 3.1
document; Core metadata and collection fields are omitted. The server does not
support OpenAPI validation, so `formatvalidated: false` records a skipped check.

```jsonc
{
  "specversion": "1.0-rc3",
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

The `GetUserProfile` operation in this example is addressed by:

```text
/apigroups/com.example.users/apis/UserProfileService.v1#operations/GetUserProfile
```

## Security Considerations

Documents, operation names, and dependency links are untrusted input. Registry
write access does not grant permission to contact the described API. Resolvers
MUST NOT invoke operations while validating or resolving a description.

External retrieval MUST require explicit policy authorization, including each
redirect target. Resolvers MUST enforce limits on document size, retrieval
count, recursion depth, and duration, and detect dependency cycles. Local file
access and private network access MUST be denied unless explicitly authorized.
Credentials MUST NOT be forwarded automatically across origins. XML parsers
MUST disable external-entity expansion; YAML parsers MUST NOT construct native
objects from document tags. These are requirements of this working-draft
extension, not additional claims about the cited description languages.

Registry authentication and authorization are separate from the API's security
requirements. API documents SHOULD describe security schemes without embedding
passwords, access tokens, or private keys. Consumers MUST apply their own trust
policy to servers and authorization URLs found in a document.

## Conformance

A registry implementing this extension MUST implement the group/resource model
and the applicable Core document, metadata, and validation rules. It is not
REQUIRED to implement every language parser or an operation resolver. A resolver
claiming support for a profile MUST implement that profile's identity, escaping,
dependency, and failure rules; storage support alone is not locator support.

At the pinned Core revision, the model JSON Schema does not allow the
`validateformat`, `validatecompatibility`, or `strictvalidation` Resource
aspects used by this model. Consequently, the API model does not validate
against that normative schema.

The referenced language standards remain authoritative for API document
contents. This extension defines only the registry profiles and selectors.

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
- [OpenRPC specification][openrpc], publisher's 1.4.x page.
- [Smithy 2.0 IDL][smithyidl], [JSON AST][smithyast], and
  [model specification][smithymodel], publisher's maintained 2.0 references.

### Informative References

- [xRegistry Schema Registry][schema], document-store and deep-reference precedent.
- [xRegistry Endpoint Registry][endpoint] and [Message Registry][message],
  asynchronous delivery and message definitions.
- [JSON-RPC 2.0][jsonrpc], wire protocol described by OpenRPC.

[core]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/spec.md
[capabilities]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/spec.md#registry-capabilities
[model]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/model.md
[modelschema]: https://github.com/xregistry/spec/blob/adf5b6a63e60c3baa78e844da8b7ce2a0d60c179/core/model.schema.json
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
[jsonrpc]: https://www.jsonrpc.org/specification
[smithyidl]: https://smithy.io/2.0/spec/idl.html
[smithyast]: https://smithy.io/2.0/spec/json-ast.html
[smithymodel]: https://smithy.io/2.0/spec/model.html
