# Pagination - Version 0.1-wip

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
the initial request for the set. If the results can not fit within one
response then these attributes MUST NOT be added to subsequent requests
by the client. Note that the server MAY include these attributes within
the URI-reference returned in a response message, but the client MUST NOT
modify those values.

#### limit

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the maximum number of records per message
  that the client is willing to accept. If the server is unable to
  meet this criterion then it MUST generate an error.
  There is no default value for this attribute.
  If this attribute is not specified, then the server MAY choose to send back
  as many or as few records per response message.
- Constraints:
  - OPTIONAL.
  - MUST be an unsigned 64-bit integer with a value greater than 0.
- Examples:
  - `100`

## Server Response

When a server returns a subset of records and more records remain, it MUST
provide a `next` link so the client can retrieve the next subset. Other
relations MAY be offered as described below.

### Server Attributes

The following attributes describe a server's response to a request for a set
of records. Their individual constraints and the protocol binding determine
which attributes are present.

Note: in the examples listed below, the use of certain query parameters
in the response messages from the server, such as `offset` and `limit`,
are an implementation detail of the server. How the server encodes the
information it needs to retrieve a certain subset of records is not mandated by
this specification.

#### link

- Type: `URI-Reference`
- Description: A URI-Reference to a subset of records. The relationship
  of the target subset to the current subset MUST be specified by the `rel`
  attribute. This value is meant to be treated as an opaque value by the
  client. If a client uses this value in a subsequent request then it
  MUST use it as it was provided by the server. Any attempt to modify its
  value, or attributes (such as query parameters), is not defined by this
  specification and the results from the server are undefined.
- Constraints:
  - A `next` link MUST be present if more records remain after the current
    subset, and MUST NOT be present at the end of the set.
  - A `prev` link MUST NOT be present at the start of the set, and MAY be
    present otherwise.
  - `first` and `last` links are OPTIONAL, including when their target is the
    current subset. This also applies to a one-page or empty result set.
  - An offered link MUST identify a subset with the stated relationship.
    The availability of an OPTIONAL relation's target does not require that
    relation to be offered, nor does offering one relation require the others.
  - MUST be a URI-Reference as defined in
    [RFC3986](https://tools.ietf.org/html/rfc3986).
- Examples:
  - `http://example.com/people?offset=3&limit=100`
  - `http://example.com/people?id=1234`
  - `http://example.com/people?resultset=7a835`

#### rel

- Type: `String`
- Description: A string representing the relationship between the records
  available via the `link` URI-Reference and the current subset of records.
  This attribute adheres to the relation type as defined in section 3.3
  of [RFC8288](https://www.rfc-editor.org/rfc/rfc8288#section-3.3).
  This specification uses the following values, which are registered in the
  [IANA Link Relation Types registry](https://www.iana.org/assignments/link-relations/link-relations.xhtml):
  - `next` - indicates the next subset of records in the sequence of records
    being returned.
  - `prev` - indicates the previous subset of records in the sequence of
    records being returned.
  - `first` - indicates the first subset of records in the sequence of records
    being returned.
  - `last` - indicates the last subset of records in the sequence of records
    being returned.
  Unless otherwise constrained by a specification leveraging this
  specification, additional values MAY be defined.
- Constraints:
  - REQUIRED if the `link` attribute is present.
  - MUST be a string as defined by `relation-type` in
   [RFC8288](https://www.rfc-editor.org/rfc/rfc8288#section-3.3).

#### expires

- Type: `Timestamp`
- Description: Indicates when the complete set of records referenced by the
  `link` will no longer be available. When not specified, the availability
  of the data is undefined by this specification. However, it is RECOMMENDED
  that this attribute only be excluded when the data being iterated over
  is not expected to change very often and therefore the server will
  typically not need to save any state related to this client's requests.
- Constraints:
  - OPTIONAL.

#### count

- Type: `Unsigned 64-bit Integer`
- Description: Indicates the total number of records in the complete set
  referenced by the `link`. Note that this is not the number of records in any one
  message, but instead it is the aggregate count of records across all
  messages in the set.
- Constraints:
  - STRONGLY RECOMMENDED.
  - MUST be an unsigned 64-bit integer. Zero is a valid count for an empty
    result set.
  - When present, MUST be consistent with every other supplied `count` in
    `link` attributes and messages for that particular set of records.
    Omission in an intervening message does not reset an earlier count.

An omitted count does not mean zero. How a count is carried is defined by the
protocol binding.

## HTTP Binding

The following describes how the attributes defined above would appear in a
flow of HTTP messages during the retrieval of a set of records.

### Request for a record set

To request a set of records from a server, a client will send an HTTP GET
request to the server. How this URL is determined is out of scope of this
specification.

The client MAY include the `limit` attribute as part of this request. Unless
there is some out-of-band negotiation to determine a different mechanism,
the server MUST accept the `limit` attribute as a query parameter (named
`limit`, case sensitive) in the URL.

For example:
```
http://example.com/people?limit=100
```

### Response for a record set

Each successful response from the server MUST adhere to the following:
- MUST respond with an HTTP 200.
- MUST include zero or more records.
- If the response refers to the start of the set of records, then the `prev`
  Link MUST NOT be included in the response.
- If the response does not include the start of the set of records, then the
  `prev` Link MAY be included in the response.
- The response MAY include the `first` Link in any response.
- If the `limit` attribute was specified as part of the flow, the response MUST
  NOT include more records than what the `limit` attribute has indicated.
- If no more records remain after the current subset, then the `next`
  Link MUST NOT be included in the response.
- If more records remain after the current subset, then the
  `next` Link MUST be included in the response.
- The response MAY include the `last` Link in any response.
- The response MAY include the `expires` attribute in any response as an
  HTTP "Expires" header. The generic attribute is a `Timestamp`; in this
  binding its value MUST be converted to an HTTP-date, as defined in
  [RFC9111, section 5.3](https://www.rfc-editor.org/rfc/rfc9111#section-5.3)
  and [RFC9110, section 5.6.7](https://www.rfc-editor.org/rfc/rfc9110#section-5.6.7).
- When a pagination Link is included, it is STRONGLY RECOMMENDED that the
  response include the `count` attribute as a parameter on a pagination Link.
- When no pagination Link is included, the response MAY omit `count`, even
  when the server knows the total number of records.

Additionally, Links MUST appear in the HTTP response as HTTP headers using
the format described in [RFC8288](https://www.rfc-editor.org/rfc/rfc8288#section-3).

In this binding, `next` is the only relation REQUIRED when more records remain.
The `prev`, `first` and `last` relations remain OPTIONAL subject to the boundary
rules above. No `self`, `first` or `last` Link is REQUIRED solely to carry a
count, and no separate HTTP count header is defined.

When supplied, `count` is a Link extension parameter containing an unsigned
decimal integer, either as a token or an equivalent quoted-string under the
Link syntax. All supplied counts for the same record set MUST agree, whether
they occur on different Link values, different header lines or later pages.

Example 1:
```
Link: <http://example.com?limit=100&offset=3>;rel=next
Link: <http://example.com?limit=100&offset=1>;rel=prev
```

Example 2:
```
Link: <http://example.com?resultset=83d71>;rel=next
Expires: Thu, 01 Dec 2021 16:00:00 GMT
```

Example 3:
```
Link: <http://example.com?id=1001>;rel=next;count=3000
Link: <http://example.com?id=0>;rel=prev;count=3000
```

An empty result set can be returned without a pagination Link or count.
The example bodies below contain exactly the two bytes `[]`.

Example 4:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 2

[]
```

A server MAY instead offer a `first` Link for that empty set and include a
zero count. This Link is OPTIONAL, not a prerequisite for an empty response.

Example 5:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 2
Link: <https://example.com/people?resultset=empty>;rel=first;count=0

[]
```

An empty page does not necessarily indicate the end of the set. If more records
remain, `next` is REQUIRED even when no count is included. The continuation in
this example is opaque, including its percent escapes, punctuation and query
parameters.

Example 6:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 2
Link: <https://example.com/people?cursor=A%2fb%2Bc%3D,+;part=1&limit=7>;rel=next

[]
```

### Iterating over the record set

Once the record set retrieval has started, the client MAY use the Links
returned from the server to iterate through the full set of records.
Typically, the client will use the `next` Link from each response to retrieve
the next subset of records until a response is returned without a `next` Link -
indicating that it has reached the end.

Absence of `count`, or an empty current page, MUST NOT be interpreted as the end
when a `next` Link is present. Conversely, OPTIONAL `prev`, `first` or `last`
Links do not require continued forward traversal when `next` is absent.
Omitting a count does not change any count already supplied for the same set.

However, if other Links are provided by the server, then the client MAY
use those Links instead to follow a different traversal path through the
records.
