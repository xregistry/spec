# Pagination - Version 1.0-rc4

This document describes a mechanism by which a server can return a set of
records to a client in an incremental fashion. Often this will be used when
a client is doing a query for a set of records and the result set is too large
to return in one response.

## Notations and Terminology

### Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC2119](https://tools.ietf.org/html/rfc2119).

## Client Request

When a client sends a request to a server which is meant to result in a
set of records being returned, the client MAY include extra attributes
to control how those records are to be returned if the results can not
fit within one response message.

### Client Attributes

The following list of attributes MAY be included in a client's request for
a set of records from a server. The client MUST only specify these on
the initial request for the set and their presence (and values) in any
subsequent request to the server to retrieve additional records for the same
pagination sequence is dictated by the server - the client MUST NOT add or
modify them.

While this specification defines a mechanism by which clients can initiate the
pagination of a result set, servers MAY automatically initiate it themselves,
typically if the result set is very large. How the server knows that the
client supports pagination, or how clients are made aware of this possibility,
is out of scope for this specification.

The location and syntax of how these attribute appear in request messages will
be defined by the protocol binding being used.

#### limit

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the maximum number of records per message that the
  client is willing to accept. If the server is unable to meet this criterion
  then it MUST generate an error.

  There is no default value for this attribute.

  If this attribute is not specified on a request message, and the server
  chooses to not enable pagination on its own, then the server's response is
  not constrained by this specification.
- Constraints:
  - OPTIONAL.
  - MUST be an unsigned 64-bit integer with a value greater than 0.
- Examples:
  - `100`

## Server Response

When a server returns a subset of records, it MAY include additional attributes
to help the client retrieve the additional subsets of records.

### Server Attributes

The following list of attributes MAY be included in a server's response to
a client's request for a set of records. The location and syntax of how these
attribute appear in response messages will be defined by the protocol binding
being used.

Note: in the examples listed below, the use of certain query parameters
in the sample response message's `Link` URL, such as `pos`, is an
implementation detail of the server. How the server encodes the information it
needs to retrieve a certain subset of records is not mandated by this
specification.

#### link

- Type: `URI-Reference`
- Description: A URI-Reference to another subset of records. The relationship
  of the subset to the current subset MUST be specified by the
  [`rel` attribute](#rel). This value is meant to be treated as an opaque
  value by the client. If a client uses this value in a subsequent request
  then it MUST use it as it was provided by the server. Any attempt to modify
  its value, or attributes (such as query parameters), is not defined by this
  specification and the results from the server are undefined.
- Constraints:
  - REQUIRED if any pagination metadata is included in a response message.
  - MUST be a URI-Reference as defined in
    [RFC3986](https://tools.ietf.org/html/rfc3986).
- Examples:
  - `http://example.com/people?id=1234`
  - `http://example.com/people?resultset=7a835`
  - `http://example.com/people?pos=3`

#### rel

- Type: `String`
- Description: A string representing the relationship between the records
  available via the `link` URI-Reference and the current subset of records.
  This specification uses the following values as defined by
  [Link Relations Registry](https://www.iana.org/assignments/link-relations):
  in [RFC5988](https://tools.ietf.org/html/rfc5988):
  - `next` - indicates the next subset of records in the sequence of records
    being returned.
  - `prev` - indicates the previous subset of records in the sequence of
    records being returned.
  - `first` - indicates the first subset of records in the sequence of records
    being returned.
  - `last` - indicates the last subset of records in the sequence of records
    being returned.

  and the following additional value:
  - `self` - indicates the current set of records in the sequence of records
    being returned. This is mainly used to carry the metadata (e.g.
    [`offset`](#offset)) about the pagination sequence.

  Unless otherwise constrained by a specification leveraging this
  specification, additional values MAY be defined.
- Constraints:
  - REQUIRED if the `link` attribute is present.
  - If present, MUST be a non-empty string conformant with:
    [Link Relations Registry](https://www.iana.org/assignments/link-relations).
  - If the current subset of records is not the last set of records for the
    pagination sequence, then a `next` Link attribute MUST be included in the
    response message.
  - A `self` Link attribute is STRONGLY RECOMMENDED to be included in all
    responses from the server so that clients have a consistent location to
    find metadata about the current pagination sequence.
  - If the size of the entire result set can fit in one response message then
    the `self` Link attribute SHOULD still be included, however no other
    Link attribute SHOULD be present.

#### expires

- Type: `Timestamp`
- Description: Indicates when the complete set of records referenced by the
  `link` will no longer be available. When not specified the availability,
  and consistency, of the result set is undefined.

  It is RECOMMENDED that this attribute only be used when the underlying
  result set is guaranteed to not change before the date specified. For
  example, it might be used if the result set is cached to ensure that
  subsequent write operations to the server will not modify the result set.
- Constraints:
  - OPTIONAL.

#### count

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the total number of records in the complete set
  in the pagination sequence. Note that this is not the number of records in
  any one message, but instead it is the aggregate count of records across all
  messages in the set.
- Constraints:
  - OPTIONAL.
  - If present, MUST be an unsigned integer.
  - STRONGLY RECOMMENDED to appear on the `self` Link attribute.
  - MAY be present for other Link attributes, and if so, it MUST be the same
    value for all Link attributes within the same message.
  - When the complete record set does not change for the lifetime of the
    pagination requests, then this value MUST be consistent across all `link`
    attributes and messages in which it appears.

#### offset

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the offset of the first item in the referenced record
  set.
- Constraints:
  - OPTIONAL.
  - If present, MUST be an unsigned integer and MUST be 0-based; meaning, the
    first record of the first result set is `0` (zero) not `1`.
  - If the current set of records does not contain any records then this
    attribute MUST NOT be present.
  - STRONGLY RECOMMENDED to appear on the `self` Link attribute.
  - MAY be present for other Link attributes, and if so, it MUST have the
    appropriate value for the referenced set of records. For example, in
    the simple case the `next` Link attribute, its `offset` value would be
    the current `self` link's `offset` value plus the number of records in the
    current response message.

#### limit

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the maximum number of records per message that the
  server will send. This MUST be the same value that was specified in the
  client's `limit` attribute when it initiated the pagination sequence. It
  is included in response messages as a convenience for clients.
- Constraints:
  - OPTIONAL.
  - If present, MUST be an unsigned integer and MUST be the same value that
    was specified during the creation of the pagination sequence, if the
    sequence was initiated by the client. For server-initiated sequences,
    the value specified for this attribute, regardless of where it appears,
    MUST NOT change.
  - STRONGLY RECOMMENDED to appear on the `self` Link attribute.
  - MAY be present for other Link attributes.

## HTTP Binding

The following describes how the attributes defined above would appear in a
flow of HTTP messages during the retrieval of a set of records.

### Request for a record set

To request a set of records from a server, a client will send an HTTP `GET`
request to the server. How this URL is determined is out of scope of this
specification.

The client MAY include the `limit` attribute as part of this request. Unless
there is some out-of-band negotiation to determine a different mechanism,
the server MUST accept the `limit` attribute as a query parameter (named
`limit`, case sensitive) in the URL.

Example:
```
http://example.com/people?limit=100
```

### Response for a record set

Each successful response from the server MUST adhere to the following:
- MUST respond with an HTTP response code in the `2xx` range.
- MUST include zero or more records.
- If the `limit` attribute was specified as part of the initial request
  for the result set, all responses for the result set MUST NOT include more
  records than what the `limit` attribute indicated.
- If the response refers to the start of the set of records, then the `prev`
  Link MUST NOT be included in the response.
- If the response does not include the start of the set of records, then the
  `prev` Link MAY be included in the response.
- The `first` Link MAY appear in any response.
- If the response refers to the end of the set of records, then the `next`
  Link MUST NOT be included in the response.
- If the response does not refer to the end of the set of records, then the
  `next` Link MUST be included in the response.
- The `last` Link MAY appear in any response.
- The response MAY include the `expires` attribute in any response as an
  HTTP "Expires" header. If present, it MUST adhere to the HTTP-date format
  specified for
  [Expires in RFC9111](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.3).
- It is STRONGLY RECOMMENDED that all responses include the `self` Link with
  the `offset`, `limit` and `count` attributes.

Links in server response messages MUST appear as HTTP headers using the format
described in [RFC8288](https://tools.ietf.org/html/rfc8288), and adhere to
the following form:

```
Link: <URL>;rel=STRING;offset=UINT;limit=UINT;count=UINT
```

Where:
- `offset`, `limit` and `count` are OPTIONAL HTTP parameters as defined above.

Example:

Initiate a pagination request, asking for only 10 records per response:

```
GET http://example.com/?limit=10
```

The first response in the sequence of 100 items might look like:
```
HTTP/1.1 200 OK
Link: <http://example.com?seq=29182>;rel=first
Link: <http://example.com?seq=29182s>;rel=self;offset=0;limit=10;count=100
Link: <http://example.com?seq=29182n>;rel=next
Expires: Wed, 01 Dec 2021 16:00:00 GMT

... first 10 records ...
```

and the 2nd request might look like:

```
GET http://example.com?seq=29182n
```

The response might look like:
```
HTTP/1.1 200 OK
Link: <http://example.com?seq=29182>;rel=first
Link: <http://example.com?seq=29182>;rel=prev
Link: <http://example.com?seq=29182s>;rel=self;offset=10;limit=10;count=100
Link: <http://example.com?seq=29182n>;rel=next
Expires: Wed, 01 Dec 2021 16:00:00 GMT

... second 10 records ...
```

If the complete result set was only 5 records, then only the `self` Link header
might included in the first response:

```
Link: <http://example.com?seq=29182>;rel=self;offset=0;limit=10;count=5
```

### Iterating over the record set

Once the record set retrieval has started, the client MAY use the Links
returned from the server to iterate through the full set of records.
Typically, the client will use the `next` Link from each response to retrieve
the next subset of records until a response is returned without a `next` Link -
indicating that it has reached the end.

For each record set returned, typically, the client will use the `self` Link's
metadata in any end-user facing interfaces to indicate which page they are
viewing. For example, using the above example's 2nd response's metadata:

```
Showing: 11-20 of 100 records
```

However, if other Links are provided by the server, then the client MAY
use those Links instead to follow a different traversal path through the
records.
