# xRegistry Events

## Abstract

This specification defines the events that an xRegistry server MAY generate.

## Table of Contents

- [Overview](#overview)
- [Notations and Terminology](#notations-and-terminology)
  - [Notational Conventions](#notational-conventions)
- [Event Definition](#event-definition)
- [Entity Events](#entity-events)
- [Sample xRegistry Interactions](#sample-xregistry-interactions)

## Overview

As updates are made to entities within an xRegistry instance, events SHOULD
be generated to notify interested parties of those changes. This specification
defines the metadata associated with each event as
[CloudEvent][https://cloudevents.io) context attributes. Whether CloudEvents
are used in the generation/serialization of the events is OPTIONAL, but it is
RECOMMENDED.

This specification does not mandate the mechanisms by which events are sent
to consumers, nor does it mandate how consumers register interest in receiving
events.

Below is a sample event serialized as a "structured" JSON CloudEvent due to a
Group's `name` being changed:

```yaml
{
  "specversion": "1.0",
  "type": "io.xregistry.group.updated",
  "source": "https://example.com",
  "subject": "/dirs/d1",
  "id": "A234-1234-1234",
  "time": "2025-09-01T12:01:02Z",
  "xregcorrelationid": "B9282-129301",
  "data": {
    "changed": [ "epoch", "modifiedat", "name" ]
  }
}
```

## Notations and Terminology

### Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

In the pseudo JSON format snippets `?` means the preceding item is OPTIONAL,
`*` means the preceding item MAY appear zero or more times, and `+` means the
preceding item MUST appear at least once. The presence of the `#` character
means the remaining portion of the line is a comment. Whitespace characters in
the JSON snippets are used for readability and are not normative.

Use of `<...>` the notation indicates a substitutable value where that is
meant to be replaced with a runtime situational-specific value as defined by
the word/phase in the angled brackets. For example `<NAME>` might be expected
to be replaced by the "name" of the item being discussed.

## Event Definition

Notification of changes to the entities within an xRegistry instance SHOULD be
exposed as events. These changes could be the result of an end-user interaction
with the Registry, or due to some other (possibly internal) processing of
the Registry data.

A single interaction with the Registry MAY result in multiple events, however,
within the scope of one interaction (see
[`xregcorrelationid`](#xregcorrelationid-extension-context-attribute)) the
following constraints apply:
- Only one of `created`, `updated` or `deleted` event MUST be generated per
  `subject`.
- If the interaction involved more than one of those actions, then the single
  event generated MUST be chosen in the following order of precedence:
  `deleted`, `created`, `updated`.
- Only one event with the same `type` and `subject` combination MUST be
  generated.

The following sections specify the metadata defined for xRegistry events.
Implementations MAY define additional metadata.

### CloudEvent [`type`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type) Core Context Attribute

The type of action taken on the entity. The value MUST be of the form:
    `io.xregistry.<ENTITY>.<ACTION>`
where:
- `<ENTITY>` is the type of xRegistry entity
  ([`subject`](#cloudevent-subject-core-context-attribute)) that was acted
  upon. It MUST be one of:
  - `registry`
  - `model`
  - `modelsource`
  - `capabilities`
  - `group`
  - `resource`
  - `version`

- `<ACTION>` is the operation performed on the entity. It MUST be one of:
  - `created`
  - `updated`
  - `deprecation`
  - `deleted`

  Not all `<ACTION>` values are applicable to all entities. See the
  [Entity Events](#entity-events) section for more information.

This context attribute MUST be present in each event.

### CloudEvent [`source`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1) Core Context Attribute

The xRegistry in which the entity exists. The value MUST be an absolute URL
to the root of the xRegistry instance.

This context attribute MUST be present in each event.

### CloudEvent [`subject`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#subject) Core Context Attribute

The `xid` of the entity acted upon. While this attribute is OPTIONAL in the
CloudEvents specification, it is REQUIRED to be present in an xRegistry event.

Note: constructing a URL by appending the `subject` value to the `source`
value MUST result in an absolute URL to the entity (assuming any trailing `/`
on `source` is removed since XIDs always start with `/`).

This context attribute MUST be present in each event.

### CloudEvent [`time`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#time) Core Context Attribute

The time of when the interaction occurred. This value MUST be the same for
all events generated within the same interaction.

Its value MUST be an [RFC3339](https://tools.ietf.org/html/rfc3339) timestamp
normalized to UTC. Use of a `time-zone` notation is RECOMMENDED. The value
used SHOULD match the current date/time used by the Registry during the
processing of the interaction. Typically, this will be the `modifiedat` value
assigned to the entities being processed.

This context attribute is NOT REQUIRED to be present in the event, but is
RECOMMENDED.

### `xregcorrelationid` Extension Context Attribute

A value that uniquely identifies the interaction in which one or more events
occurred. This value has the following constraints:
- MUST be a non-empty string.
- MUST be case-insensitively unique within the scope of the Registry instance,
  for the lifetime of the Registry.
- All events generated from the same interaction MUST have the same
  `xregcorrelationid` value. Conceptually, this can be thought of as the
  "transaction ID" of the interaction.

When an interaction has a request-response message exchange pattern, and
`xregcorrelationid` values are included in resulting events, then the response
message for the interaction MUST include this value. In the case of an HTTP
interaction, the following HTTP header MUST be present in the response flow:

```yaml
xRegistry-xregcorrelationid: <STRING>
```

This allows for clients to identify which events were generated as a result of
each request-response operation.

This context attribute is NOT REQUIRED to be present in the event, but is
RECOMMENDED.

### CloudEvent [`data`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#event-data)

When present, and serialized in JSON, the `data` MUST be of the form:

```yaml
{
  "changed": [ "<STRING>", * ] ?
}
```

The `changed` attribute, when present, has the following constraints:
- MUST be a list of the top-level attribute names (not values) that were
  added, modified, or deleted for the `subject` entity.

- In the case of changing a Resource's default Version pointer, the list MUST
  include all attributes from the previous default Version that have non-`null`
  values, and all attributes from the new default Version that have non-`null`
  values. Any duplicate attribute names MUST be removed.

- This attribute MUST NOT appear on the `created` or `deleted` events.

- This specification does not mandate any particular order to the attribute
  names in the array.

There are certain events where non-top-level attributes are included, and
those will be noted in the [Entity Events](#entity-events) sections below.
When they do appear they MUST use the JSONPath dot (`.`) notation to express
the traversal to the attribute of interest.

If an entity is updated for multiple reasons during the processing of an
interaction, per the rules previously stated, only one `updated` event
will be generated. This means the attribute names of all impacted attributes
MUST be merged into one `changed` list.

While `changed` is OPTIONAL, it is RECOMMENDED to be present on event where
it is permitted due to its usefulness for consumers. However, if exposure of
this information would be inappropriate for some scenarios then it MAY be
excluded. For example, for privacy/security reasons.

While this specification only shows `data` being present when `changed` is
permitted, implementations MAY define their own metadata to be included
in the `data` of a CloudEvent.

This metadata (`data`) is NOT REQUIRED to be present in the event, but is
RECOMMENDED.

## Entity Events

This section defines which `<ACTION>` values are applicable for each `<ENTITY>`
value.

### `registry` Events

- Action: `updated`
  - MUST be generated when a Registry's attribute is updated, where each
    modified attribute MUST be included in `changed`, if present.

  - MUST be generated when a Group is created or deleted, where `changed`, if
    present, includes (at least) `epoch`, `modifiedat`, `<GROUPS>` and
    `<GROUPS>count` attributes names.

    While the `<GROUPS>` attribute is present in `changed` due to the child
    collection changing, in order to see which specific Groups were impacted
    the `io.xregistry.group.created` and `io.xregistry.group.deleted` events
    would need to be examined.

  - MUST be generated when `model`, `modelsource` or `capabilities` are
    updated and the appropriate attribute MUST appear in `changed`, if present.

The `io.xregistry.registry.created` and `io.xregistry.registry.updated` events
are not defined as part of this specification as those operations are not
defined in the xRegistry specification. It is expected that the tooling that
performs those operations will define those events, if needed.

### `model` Events

- Action: `updated`
  - MUST be generated when the Registry's model is updated. This might occur
    due to a user action (e.g. updating `modelsource`) or an internal (system)
    action.

  - MUST NOT include a `changed` list.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `model` attribute will be included in `changed`, if present.

Often `io.xregistry.model.updated` and `io.xregistry.modelsource.updated`
will be generated at the same time since model updates are most likely done
by changing the `modelsource` attribute. However, since the `model` might
change for other reasons, users who are interested in all `model` changes need
to watch for `io.xregistry.model.update` events, not
`io.xregistry.modelsource.updated` events.

### `modelsource` Events

- Action: `updated`
  - MUST be generated when the Registry's `modelsource` attribute is updated.

  - MUST NOT include a `changed` list.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `modelsource` attribute will be included in `changed`, if present.

Often `io.xregistry.model.updated` and `io.xregistry.modelsource.updated`
will be generated at the same time since model updates are most likely done
by changing the `modelsource` attribute. However, since the `model` might
change for other reasons, users who are only interested in changes related
to user modifications of the model need to watch for
`io.xregistry.modelsource.update` events, not `io.xregistry.model.updated`
events.

### `capabilities` Events

- Action: `updated`
  - MUST be generated when a Registry's capabilities are updated, where
    the top-level capability names are included in `changed`, if present.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `capabilities` attribute will be included in `changed`, if present.

### `group` Events

- Action: `created`
  - MUST be generated when a new Group is created.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `<GROUPS>` and `<GROUPS>count` attributes will be included in `changed`,
    if present.

- Action: `updated`
  - MUST be generated when a Group's attribute is updated, where each modified
    attribute MUST be included in `changed`, if present.

  - MUST be generated when a Resource is created or deleted, where `changed`,
    if present, includes (at least) `epoch`, `modifiedat`, `<RESOURCES>` and
    `<RESOURCES>count` attributes names.

    While the `<RESOURCES>` attribute is present due to the child
    collection changing, in order to see which specific Resources were impacted
    the `io.xregistry.resource.created` and `io.xregistry.resource.deleted`
    events would need to be examined.

    This includes any updates to the `deprecated` sub-object, even
    though a `io.xregistry.group.deprecation` event is also generated. And
    in that situation just `deprecated` would be included in `changed`,
    if present. To see which specific top-level `deprecated` attributes were
    changed, the `io.xregistry.group.deprecation` event would need to be
    examined.

- Action: `deprecation`
  - MUST be generated when a Group's `deprecated` sub-object is set,
    deleted or any of its attributes updated, where "changed", if present,
    includes the list of top-level attribute names from the `deprecated`
    sub-object that were modified.

  - A `io.xregistry.group.updated` event will also be generated where the
    `deprecated` attribute will be included in `changed`, if present.

- Action: `deleted`
  - MUST be generated when a Group is deleted.

  - A `io.xregistry.registry.updated` event will also be generated where the
   `<GROUPS>` and `<GROUPS>count` attributes will be included in `changed`, if
   present.

### `resource` Events

- Action: `created`
  - MUST be generated when a new Resource is created, where each modified
    attribute MUST be included in `changed`, if present.

  - At least one `io.xregistry.version.created` event will also be
    generated since at least one Version will also be created.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `<RESOURCES>` and `<RESOURCES>count` attributes will be included in
    `changed`, if present.

- Action: `updated`
  - MUST be generated when a Resource's (default Version) attribute is updated,
    where each modified attribute MUST be included in `changed`, if present.

  - MUST be generated when a Resource's `meta` attribute is updated, where
    `changed`, if present, includes (at least) the changed top-level `meta`
    attributes names prefixed with `meta.`. For example,
    `meta.defaultversionid`.

    This includes any updates to the `deprecated` sub-object, even
    though a `io.xregistry.resource.deprecation` event is also generated. And
    in that situation just `meta.deprecated` would be included in `changed`,
    if present. To see which specific top-level `deprecated` attributes were
    changed, the `io.xregistry.resource.deprecation` event would need to be
    examined.

  - MUST be generated when a Version is created or deleted, where `changed`,
    if present, includes (at least) `meta.epoch`, `meta.modifiedat`,
    `versions` and `versionscount` attributes names.

    While the `version` attribute is present due to the child
    collection changing, in order to see which specific Versions were impacted
    the `io.xregistry.version.created` and `io.xregistry.version.deleted`
    events would need to be examined.

  - Updating a Resource's `meta.defaultversionid` attribute will
    generate a `io.xregistry.resource.updated` event but it MUST NOT generate
    a `io.xregistry.version.updated` event for either the prior or new default
    Version.

- Action: `deprecation`
  - MUST be generated when a Resource's `meta.deprecated` sub-object is set,
    deleted or any of its attributes updated, where "changed", if present,
    includes the list of top-level attribute names from the `deprecated`
    sub-object that were modified.

  - A `io.xregistry.resource.updated` event will also be generated where the
    `deprecated` attribute will be included in `changed`, if present.

- Action: `deleted`
  - MUST be generated when a Resource is deleted.

  - A `io.xregistry.version.deleted` event will also be generated for
    each Version.

  - A `io.xregistry.registry.updated` event will also be generated where the
    `<RESOURCES>` and `<RESOURCES>count` attributes will be included in
    `changed`, if present.

### `version` Events

- Action: `created`
  - MUST be generated when a new Version is created.

  - A `io.xregistry.resource.updated` event will also be generated where the
    `versions` and `versionscount` attributes will be included in `changed`, if
    present.

- Action: `updated`
  - MUST be generated when a Version attribute is updated, where each modified
    attribute MUST be included in `changed`, if present.

- Action: `deleted`
  - MUST be generated when a Version is deleted.

  - A `io.xregistry.resource.updated` event will also be generated where the
    `versions` and `versionscount` attributes will be included in `changed`, if
    present.

## Sample xRegistry Interactions

In these examples, unless otherwise stated, assume that the Registry has
the following model definition:

```yaml
{
  "groups": {
    "dirs": {
      "singular": "dir",
      "resources": {
        "files": {
          "singular": "file"
        }
      }
    }
  }
}
```

### Update a Registry attribute

- Interaction:
  - `PATCH /`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.registry.updated`
    - Subject: `/`
    - Changed: `epoch`, `modifiedat`, `name`

### Create a tree of entities

- Empty Registry
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v1`
  - Body: `{}`
- Events:
  - `io.xregistry.registry.updated`
    - Subject: `/`
    - Changed: `epoch`, `modifiedat`, `dirs`, `dirscount`
  - `io.xregistry.group.created`
    - Subject: `/dirs/d1`
  - `io.xregistry.resource.created`
    - Subject: `/dirs/d1/files/f1`
  - `io.xregistry.version.created`
    - Subject: `/dirs/d1/files/f1/versions/v1`

### Update a Resource attribute (a default Version attribute)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - Subject: `/dirs/d1/files/f1/version/v1`
    - Changed: `epoch`, `modifiedat`, `name`

### Update a Resource's meta sub-object

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibilityauthority": "server" }`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.epoch`, `meta.modifiedat`, `meta.compatibilityauthority`

### Update a Resource's meta sub-object and deprecate the Resource

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibilityauthority": "server", "deprecated": {...} }`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.epoch`, `meta.modifiedat`, `meta.compatibilityauthority`,
      `meta.deprecated`
  - `io.xregistry.resource.deprecation`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `<DEPRECATED-ATTRIBUTES-CHANGED-IF-ANY>`

### Import an entire Registry

- Empty Registry
- Interaction:
  - `PUT /`
  - Body: Registry attributes, `modelsource`, `capabilities`, Groups,
    Resources, Versions
- Events:
  - `io.xregistry.registry.updated`
    - Subject: `/`
    - Changed: `epoch`, `modifiedat`, `model`, `modelsource`, `capabilities`,
      `<GROUPS>`, `<GROUPS>count`, `<OTHER-REGISTRY-ATTRIBUTES>`
  - `io.xregistry.model.updated`
    - Subject: `/model`
  - `io.xregistry.modelsource.updated`
    - Subject: `/modelsource`
  - `io.xregistry.capabilities.updated`
    - Subject: `/capabilities`
  - `io.xregistry.group.created` for each new Group
    - Subject: `/dirs/d1`
  - `io.xregistry.resource.created` for each new Resource
    - Subject: `/dirs/d1/files/f1`
  - `io.xregistry.version.created` for each new Version
    - Subject: `/dirs/d1/files/f1/versions/v1`

### Create a new Version - non-sticky

- Current default Version (v1) is not "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
      `versions`, `versionscount`,
      `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - Subject: `/dirs/d1/files/f1/versions/v2`

### Create a new Version - sticky

- Current default Version (v1) is "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - Subject: `/dirs/d1/files/f1/versions/v2`

### Change `defaultversionid` pointer

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "defaultversionid": "v2" }`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`

  Note the no `io.xregistry.version.updated` event is generated.

### Update a Version attribute (the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v1`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - Subject: `/dirs/d1/files/f1/version/v1`
    - Changed: `epoch`, `modifiedat`, `name`

### Update a Version attribute (not the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v2`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.version.updated`
    - Subject: `/dirs/d1/files/f1/version/v2`
    - Changed: `epoch`, `modifiedat`, `name`

### Create a new Version - not sticky

- Current default Version is `v1`
- Interaction:
  - `POST /dirs/d1/files/f1`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `versions`, `versionscount`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - Subject: `/dirs/d1/files/f1/version/v2`

### Create a new Version - sticky

- Current default Version is `v1`
- Interaction:
  - `POST /dirs/d1/files/f1`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - Subject: `/dirs/d1/files/f1`
    - Changed: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - Subject: `/dirs/d1/files/f1/version/v2`

### Delete a Group

- Interaction:
  - `DELETE /dirs/d1`
- Events:
  - `io.xregistry.registry.updated`
    - Subject: `/`
    - Changed: `dirs`, `dirscount`, `epoch`, `modifiedat`
  - `io.xregistry.group.deleted`
    - Subject: `/dirs/d1`
  - `io.xregistry.resource.deleted` for each deleted Resource
    - Subject: `/dirs/d1/files/f1`
  - `io.xregistry.version.deleted` for each deleted Version
    - Subject: `/dirs/d1/files/f1/versions/v1`

### Creating a Group with complete client HTTP message exchange

Client Request:
```yaml
PUT /dirs/d1
Host: example.com
Content-Type: application/json

{}
```

xRegistry Response:

```yaml
HTTP/1.1 200 OK
Content-Type: application/json
Date: Wed, 02 Jul 2025 12:00:01 GMT
xRegistry-xregcorrelationid: B9282-129301

{
  "dirid": "d1",
  "self": "http://example.com/dirs/d1",
  "xid": "/dirs/d1",
  "epoch": 1,
  "createdat": "2025-07-02T12:00:01Z",
  "modifiedat": "2025-07-02T12:00:01Z",

  "filesurl": "http://example.com/dirs/d1/files",
  "filescount": 0
}
```

Events Generated:

```yaml
{
  "specversion": "1.0",
  "type": "io.xregistry.registry.updated",
  "source": "https://example.com",
  "subject": "/",
  "id": "A234-1234-1234",
  "time": "2025-07-02T12:00:01Z",
  "xregcorrelationid": "B9282-129301",
  "data": {
    "changed": [ "dirs", "dirscount", "epoch", "modifiedat" ]
  }
}
```

```yaml
{
  "specversion": "1.0",
  "type": "io.xregistry.group.created",
  "source": "https://example.com",
  "subject": "/dirs/d1",
  "id": "A432-4321-4321",
  "time": "2025-07-02T12:00:01Z",
  "xregcorrelationid": "B9282-129301"
}
```
