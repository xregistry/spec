# xRegistry Events

<!-- words: eventreceiver xreginstance-->

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
be generated to notify interested parties of those changes. The events defined
by this specification are defined as CloudEvents and implementations MUST
generate events that are compliant with the
[CloudEvents specification](https://cloudevents.io).

This specification does not mandate the mechanisms by which events are sent
to consumers, nor does it mandate how consumers register interest in receiving
events.

Below is a sample event payload (the CloudEvents `data` context attribute)
serialized in JSON:

```yaml
{
  "action": "io.xregistry.group.updated",
  "registry": "https://example.com",
  "xid": "/dirs/d1",
  "time": "2025-09-01T12:01:02Z",
  "instance": "B9282-129301",
  "epoch": 5,
  "changed": [ "epoch", "modifiedat", "name" ]
}
```

When serialized as a "binary" CloudEvent, over HTTP, it would look like:

```yaml
POST /eventReceiver HTTP/1.1
Host: ...
ce-specversion: 1.0
ce-type: io.xregistry.group.updated
ce-source: https://example.com
ce-subject: /dirs/d1
ce-id: A234-1234-1234
ce-time: 2025-09-01T12:01:02Z
ce-xreginstance: B9282-129301
Content-Type: application/json; charset=utf-8
Content-Length: ...

{
  "action": "io.xregistry.group.updated",
  "registry": "https://example.com",
  "xid": "/dirs/d1",
  "time": "2025-09-01T12:01:02Z",
  "instance": "B9282-129301",
  "epoch": 5,
  "changed": [ "epoch", "modifiedat", "name" ]
}
```

and when serialized as a "structured" CloudEvent, it would look like:

```yaml
{
  "specversion": "1.0",
  "type": "io.xregistry.group.updated",
  "source": "https://example.com",
  "subject": "/dirs/d1",
  "id": "A234-1234-1234",
  "time": "2025-09-01T12:01:02Z",
  "xreginstance": "B9282-129301",

  "data": {
    "action": "io.xregistry.group.updated",
    "registry": "https://example.com",
    "xid": "/dirs/d1",
    "time": "2025-09-01T12:01:02Z",
    "instance": "B9282-129301",
    "epoch": 5,
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

Use of the `<...>` notation indicates a substitutable value that is
meant to be replaced with a runtime situation-specific value as defined by
the word/phrase in the angled brackets. For example `<NAME>` might be expected
to be replaced by the "name" of the item being discussed.

## Event Definition

Notification of changes to the entities within an xRegistry instance SHOULD be
exposed as events. These changes could be the result of an end-user interaction
with the Registry, or due to some other (possibly internal) processing of
the Registry data.

A single interaction with the Registry MAY result in multiple events; however,
within the scope of one interaction (see [`instance`](#instance)), the
following constraints apply:
- At most one `created`, `updated` or `deleted` event MUST be generated
  per entity.
- If the interaction involved more than one of those actions, then the single
  event generated MUST be chosen in the following order of precedence:
  `deleted`, `created`, `updated`.
- Only one event with the same `action` and `xid` combination MUST be generated.

The following sections specify the payload attributes defined for xRegistry
events. Implementations MAY define additional attributes.

Notes about the use of CloudEvents:
- Not all CloudEvents context attributes are fully described in this
  specification. Implementations MUST adhere to the
  [CloudEvents](https://cloudevents.io) specification.
- For CloudEvents context attributes that are not explicitly defined (such as
  `id`), unless otherwise stated, implementations are free to chose an
  appropriate value.
- Some xRegistry event attributes will appear to be duplicated in the
  CloudEvents context attributes. This is to allow for middleware to examine
  these fields without the need to examine the event payload - one of the
  main benefits of CloudEvents.

### `action`

This REQUIRED attribute's value MUST be a string indicating the action taken
on the entity in question.

The value MUST be of the form:
    `io.xregistry.<ENTITY>.<ACTION>`

where:
- `<ENTITY>` is the type of xRegistry entity that was acted upon. It MUST be
  one of:
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
  - `deprecated`
  - `deleted`

  Not all `<ACTION>` values are applicable to all entities. See the
  [Entity Events](#entity-events) section for more information.

This value MUST also appear as the CloudEvents
[`type`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type)
content attribute.

Example:
- `"action": "io.xregistry.resource.updated"`

### `registry`

This REQUIRED attribute MUST be an absolute URL to the root of the xRegistry
in which the entity exists.

This value MUST also appear as the CloudEvents
[`source`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1)
context attribute.

Example:
- `"registry": "https://registry.example.com"`

### `xid`

This REQUIRED attribute MUST be the xRegistry XID of the entity.

This value MUST also appear as the CloudEvents
[`subject`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#subject)
context attribute. While `subject` is OPTIONAL in the CloudEvents specification,
it is REQUIRED to be present in an xRegistry event.

Note: constructing a URL by appending the `xid`/`subject` value to the
`registry`/`source` value MUST result in an absolute URL to the entity
(assuming any trailing `/` on `registry` is removed since XIDs always start
with `/`).

Example:
- `"xid": "/dirs/d1/files/f1"`

### `time`

This OPTIONAL, but RECOMMENDED, attribute is the time when the interaction
occurred. This value MUST be the same for all events generated within the same
[instance](#instance) and MUST match the xRegistry timestamp (value and
xRegistry specification defined timestamp format) used for the interaction -
this will typically be the `modifiedat` value assigned to the entities being
processed.

The CloudEvents
[`time`](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#time)
context attribute is OPTIONAL but RECOMMENDED. Its value MAY differ from the
payload's `time` attribute if the CloudEvents processor is separate from the
original event's processing.

Example:
- `"time": "2025-09-01T12:01:02Z"`

### `instance`

This OPTIONAL, but RECOMMENDED, attribute is the [xRegistry Interaction
Instance value](spec.md#xregistry-interaction-instances). A value that uniquely
identifies the interaction in which one or more events occurred.

Example:
- `"instance": "B9282-129301"`

This value, if defined, MUST appear as a CloudEvents extension attribute
named `xreginstance`. For example:

```yaml
ce-xreginstance: B9282-129301
```

as an HTTP header in CloudEvents binary mode, or:

```yaml
"xreginstance": "B9282-129301"
```

as a JSON attribute in CloudEvents structured mode.

### `epoch`

This attribute is the entity's `epoch` value as seen at the end of the
interaction. This MUST be included in `created` and `updated` events for
Registries, Groups, Resources and Versions. It MUST NOT be present in
`deleted` events. For all other entities or events, this attribute MUST NOT
appear.

Example:
- `"epoch": 12`

### `meta.epoch`

When a Resource (not a Version or a Resource's "meta" sub-object) is the
entity in question, this attribute's value MUST be the Resource's `meta.epoch`
value as seen at the end of the interaction.

It MUST appear for `created` and `updated` Resource events. It MUST NOT
be included for Resource `deleted` events.

Note that Resource `created` and `updated` events will include both `epoch`
and `meta.epoch` attributes even if one of them didn't change for the
interaction.

Example:
- `"meta.epoch": 5`

### `changed`

This OPTIONAL attribute MAY be included to indicate which attributes
of the entity were modified. When present, has the following constraints:

  - MUST be a list of the top-level attribute names (not values) that were
    added, modified, or deleted for the entity.

  - This attribute MUST NOT appear on the `created`, `deleted`, or `deprecated`
    events.

  - This specification does not mandate any particular order for the attribute
    names in the array.

  - There are certain events where non-top-level attributes are included, and
    those will be noted in the [Entity Events](#entity-events) sections below.
    When they do appear they MUST use the
    [xRegistry Dot (`.`) Notation](spec.md#xregistry-dot--notation) to express
    the traversal to the attribute of interest.

  - While `changed` is OPTIONAL, it is RECOMMENDED to be present on an event
    where it is permitted due to its usefulness for consumers. However, if
    exposure of this information would be inappropriate for some scenarios
    then it MAY be excluded. For example, for privacy/security reasons.

  - If an entity is updated for multiple reasons during the processing of an
    interaction, per the rules previously stated, there MUST only be one
    `updated` event be generated. This means the attribute names of all
    impacted attributes MUST be merged into one `changed` list.

Example:
- `"changed": [ "epoch", "modifiedat", "name" ]`

## Event Serialization

The complete payload of the event MUST be serialized as:

```yaml
{
  "action": "<STRING>",
  "registry": "<URL>",
  "xid": "<XID>",
  "time": "<TIMESTAMP>", ?
  "instance": "<STRING>", ?
  "epoch": UINTEGER, ?
  "meta.epoch": UINTEGER, ?
  "changed": [ "<STRING>", * ] ?
}
```

A JSON Schema for this payload is available in [events.json](events.json).

## Entity Events

This section defines which `<ACTION>` values are applicable for each `<ENTITY>`
value.

### `registry` Events

- Action: `created`
  - STRONGLY RECOMMENDED to be generated when a new Registry is created.
    This event isn't mandated since the action of creating a new Registry
    is not defined in the xRegistry specification, and therefore (technically)
    out of scope. However, for interoperability, the suggested event is defined
    here.

  - If, during the process of creating a new Registry, the model, modelsource
    or entities are modified/created, then events for those actions MUST be
    generated as well.

- Action: `updated`
  - MUST be generated when a Registry's attribute is updated, where each
    modified attribute MUST be included in `changed`, if present.

  - MUST be generated when a Group is created or deleted, where `changed`, if
    present, MUST include `epoch`, `modifiedat`, `<GROUPS>` and `<GROUPS>count`
    attribute names.

    While the `<GROUPS>` attribute is present in `changed` due to the child
    collection changing, in order to see which specific Groups were impacted,
    the `io.xregistry.group.created` and `io.xregistry.group.deleted` events
    would need to be examined.

  - MUST be generated when `model`, `modelsource` or `capabilities` are
    updated and the appropriate attribute MUST appear in `changed`, if present.

- Action: `deleted`
  - STRONGLY RECOMMENDED to be generated when a Registry is deleted.
    This event isn't mandated since the action of deleting a new Registry
    is not defined in the xRegistry specification, and therefore (technically)
    out of scope. However, for interoperability, the suggested event is defined
    here.

  - It is STRONGLY RECOMMENDED that a `deleted` event be generated for each
    entity within the deleted Registry. The optionality of this requirement
    is to allow for situations where implementations (or users) might view
    such a large volume of events to be problematic in their use cases.

### `model` Events

- Action: `updated`
  - MUST be generated when the Registry's model is updated. This might occur
    due to a user action (e.g. updating `modelsource`) or an internal (system)
    action.

  - MUST NOT include a `changed` list.

  - An `io.xregistry.registry.updated` event MUST also be generated where the
    `model` attribute MUST be included in `changed`, if present.

Often `io.xregistry.model.updated` and `io.xregistry.modelsource.updated`
will be generated at the same time since model updates are most likely done
by changing the `modelsource` attribute. However, since the `model` might
change for other reasons, users who are interested in all `model` changes need
to watch for `io.xregistry.model.updated` events, not
`io.xregistry.modelsource.updated` events.

### `modelsource` Events

- Action: `updated`
  - MUST be generated when the Registry's `modelsource` attribute is updated.

  - MUST NOT include a `changed` list.

  - An `io.xregistry.registry.updated` event MUST also be generated where the
    `modelsource` attribute MUST be included in `changed`, if present.

Often `io.xregistry.model.updated` and `io.xregistry.modelsource.updated`
will be generated at the same time since model updates are most likely done
by changing the `modelsource` attribute. However, since the `model` might
change for other reasons, users who are only interested in changes related
to user modifications of the model need to watch for
`io.xregistry.modelsource.updated` events, not `io.xregistry.model.updated`
events.

### `capabilities` Events

- Action: `updated`
  - MUST be generated when a Registry's capabilities are updated, where
    the top-level capability names are included in `changed`, if present.

  - An `io.xregistry.registry.updated` event MUST also be generated where the
    `capabilities` attribute MUST be included in `changed`, if present.

### `group` Events

- Action: `created`
  - MUST be generated when a new Group is created.

  - An `io.xregistry.registry.updated` event MUST also be generated where
    `changed`, if present, MUST include `epoch`, `modifiedat`, `<GROUPS>` and
    `<GROUPS>count` attribute names.

- Action: `updated`
  - MUST be generated when a Group's attribute is updated, where each modified
    attribute MUST be included in `changed`, if present.

  - MUST be generated when a Resource is created or deleted, where `changed`,
    if present, MUST include `epoch`, `modifiedat`, `<RESOURCES>` and
    `<RESOURCES>count` attribute names.

    While the `<RESOURCES>` attribute is present due to the child
    collection changing, in order to see which specific Resources were impacted,
    the `io.xregistry.resource.created` and `io.xregistry.resource.deleted`
    events would need to be examined.

    This MUST include any updates to the `deprecated` sub-object, even
    though a `io.xregistry.group.deprecated` event is also generated. And
    in that situation `deprecated` MUST be included in the
    `io.xregistry.group.updated` event's `changed` list, if present.

- Action: `deprecated`
  - MUST be generated when a Group's `deprecated` sub-object is set, deleted or
    any of its attributes are updated. Note, a `changed` list MUST NOT be
    included. Note, deleting the `deprecated` sub-object in a production
    environment is discouraged.

  - An `io.xregistry.group.updated` event MUST also be generated where
    `changed`, if present, MUST include `epoch`, `modifiedat` and
    `deprecated` attribute names.

- Action: `deleted`
  - MUST be generated when a Group is deleted.

  - An `io.xregistry.registry.updated` event MUST also be generated where
    `changed`, if present, MUST include `epoch`, `modifiedat`, `<GROUPS>` and
    `<GROUPS>count` attribute names.

### `resource` Events

- Action: `created`
  - MUST be generated when a new Resource is created.

  - At least one `io.xregistry.version.created` event MUST also be
    generated since at least one Version MUST also be created.

  - An `io.xregistry.group.updated` event MUST also be generated where the
    `changed`, if present, MUST include `epoch`, `modifiedat`, `<RESOURCES>`
    and `<RESOURCES>count` attributes names.

- Action: `updated`
  - MUST be generated when:
    - A Resource's attribute (from the default Version entity) is updated,
      where `changed`, if present, MUST include each modified attribute. Note
      that a `io.xregistry.version.updated` event MUST also be generated.

    - A Version is created or deleted, where `changed`, if present, MUST
      include `meta.epoch`, `meta.modifiedat`, `versions` and `versionscount`
      attribute names.

      While the `versions` attribute is present due to the child collection
      changing, in order to see which specific Versions were impacted, the
      `io.xregistry.version.created` and `io.xregistry.version.deleted` events
      would need to be examined.

    - A Resource's `meta` sub-object is update, where `changed`, if present,
      MUST include the changed top-level `meta` attribute names prefixes with
      `meta.`. For example, `meta.defaultversionid`.

      This MUST include any updates to the `deprecated` sub-object, even though
      a `io.xregistry.resource.deprecated` event is also generated. And in that
      situation `meta.deprecated` MUST be included in the
      `io.xregistry.resource.updated` event's `changed` list, if present.

      In the case of changing a Resource's `meta.defaultversionid` attribute,
      the `changed` list MUST include all attributes from the previous default
      Version that have non-`null` values, and all attributes from the new
      default Version that have non-`null` values. This MUST include the
      `versionid` attribute as well. Any duplicate attribute names MUST be
      removed. Note that a `io.xregistry.version.updated` event MUST NOT be
      generated for either the prior or new default Version due to the default
      Version changing.

  - When a Resource's domain-specific document that is stored within the
    Registry is modified, then the Resource's `SINGULAR` attribute MUST be
    included in `changed`, not `SINGULARbase64` - even if the `base64` variant
    is used during serialization of the Resource.

- Action: `deprecated`
  - MUST be generated when a Resource's `meta.deprecated` sub-object is set,
    deleted, or when any of its attributes are updated. Note that a `changed`
    attribute MUST NOT be be included. Note, deleting the `meta.deprecated`
    sub-object in a production environment is discouraged.

  - An `io.xregistry.resource.updated` event MUST also be generated where
    `changed`, if present, MUST include `meta.epoch`, `meta.modifiedat` and
    `meta.deprecated` attribute names.

- Action: `deleted`
  - MUST be generated when a Resource is deleted.

  - A `io.xregistry.version.deleted` event MUST also be generated for each
    Version.

  - An `io.xregistry.group.updated` event MUST also be generated where
    `changed`, if present, MUST include `epoch`, `modifiedat` and `<RESOURCES>`
    and `<RESOURCES>count` attribute names.

### `version` Events

- Action: `created`
  - MUST be generated when a new Version is created.

  - An `io.xregistry.resource.updated` event MUST also be generated where
    `changed`, if present, MUST include `meta.epoch`, `meta.modifiedat`,
    `versions` and `versionscount` attribute names.

- Action: `updated`
  - MUST be generated when a Version attribute is updated, where each modified
    attribute MUST be included in `changed`, if present. Note that a
    `io.xregistry.resource.updated` event MUST also be generated if this
    Version is also the Resource's default Version.

  - When a Versions's domain-specific document that is stored within the
    Registry is modified, then the Resource's `SINGULAR` attribute MUST be
    included in `changed`, not `SINGULARbase64` - even if the `base64` variant
    is used during serialization of the Resource.

- Action: `deleted`
  - MUST be generated when a Version is deleted.

  - An `io.xregistry.resource.updated` event MUST also be generated where
    `changed`, if present, MUST include `meta.epoch`, `meta.modifiedat`,
    `versions` and `versionscount` attribute names.

## Sample xRegistry Interactions

This section shows some xRegistry interactions and the related event data that
is generated. For brevity, the text focuses just on the most important
attributes, excluding the ones that are not very interesting (e.g. `time`)
from an educational perspective.

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
    - `xid`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Create a tree of entities

- Empty Registry
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v1$details`
  - Body: `{}`
- Events:
  - `io.xregistry.registry.updated`
    - `xid`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `dirs`, `dirscount`
  - `io.xregistry.group.created`
    - `xid`: `/dirs/d1`
    - `epoch`: Group's `epoch` value
  - `io.xregistry.resource.created`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value
    - `meta.epoch`: Resource's `meta.epoch` value
  - `io.xregistry.version.created`
    - `xid`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value

### Update a Resource attribute (a default Version attribute)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1$details`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (`v1`'s `epoch`)
    - `meta.epoch`: Resource's `meta.epoch` value (unchanged)
    - `changed`: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - `xid`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Update a Resource's meta sub-object

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibility": "backward" }`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's - unchanged)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `meta.compatibility`

### Update a Resource's meta sub-object and deprecate the Resource

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibility": "backward", "deprecated": {...} }`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's - unchanged)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `meta.compatibility`,
      `meta.deprecated`
  - `io.xregistry.resource.deprecated`
    - `xid`: `/dirs/d1/files/f1`

### Import an entire Registry

- Empty Registry
- Interaction:
  - `PUT /`
  - Body: Registry attributes, `modelsource`, `capabilities`, Groups,
    Resources, Versions
- Events:
  - `io.xregistry.registry.updated`
    - `xid`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `model`, `modelsource`, `capabilities`,
      `<GROUPS>`, `<GROUPS>count`, `<OTHER-REGISTRY-ENTITY-ATTRIBUTES>`
  - `io.xregistry.model.updated`
    - `xid`: `/model`
  - `io.xregistry.modelsource.updated`
    - `xid`: `/modelsource`
  - `io.xregistry.capabilities.updated`
    - `xid`: `/capabilities`
  - `io.xregistry.group.created` for each new Group
    - `xid`: `/dirs/d1`
    - `epoch`: Group's `epoch` value
  - `io.xregistry.resource.created` for each new Resource
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
  - `io.xregistry.version.created` for each new Version
    - `xid`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value

### Create a new Version - non-sticky

- Current default Version (v1) is not "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2$details`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
      `versions`, `versionscount`,
      `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - `xid`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Create a new Version directly - sticky

- Current default Version (v1) is "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2$details`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - `xid`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Change `defaultversionid` pointer

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "defaultversionid": "v2" }`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`

  Note that no `io.xregistry.version.updated` event is generated.

### Update a Version attribute (the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v1$details`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - `xid`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Update a Version attribute (not the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v2$details`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.version.updated`
    - `xid`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Create a new Version directly - not sticky

- Current default Version (v1) is not "sticky"
- Interaction:
  - `POST /dirs/d1/files/f1$details`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `versions`, `versionscount`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - `xid`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Create a new Version - sticky

- Current default Version (v1) is "sticky"
- Interaction:
  - `POST /dirs/d1/files/f1$details`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `xid`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - `xid`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Delete a Group

- Interaction:
  - `DELETE /dirs/d1`
- Events:
  - `io.xregistry.registry.updated`
    - `xid`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `dirs`, `dirscount`, `epoch`, `modifiedat`
  - `io.xregistry.group.deleted`
    - `xid`: `/dirs/d1`
  - `io.xregistry.resource.deleted` for each deleted Resource
    - `xid`: `/dirs/d1/files/f1`
  - `io.xregistry.version.deleted` for each deleted Version
    - `xid`: `/dirs/d1/files/f1/versions/v1`

### Creating a Group with a complete client HTTP message exchange

This will show the complete HTTP message exchange and full xRegistry events
generated.

Client Request:
```yaml
PUT /dirs/d1 HTTP/1.1
Host: example.com
Content-Type: application/json

{}
```

xRegistry Response:

```yaml
HTTP/1.1 201 Created
Location: https://example.com/dirs/d1
Content-Type: application/json
Date: Wed, 02 Jul 2025 12:00:01 GMT
xRegistry-Instance: B9282-129301

{
  "dirid": "d1",
  "self": "https://example.com/dirs/d1",
  "xid": "/dirs/d1",
  "epoch": 1,
  "createdat": "2025-07-02T12:00:01Z",
  "modifiedat": "2025-07-02T12:00:01Z",

  "filesurl": "https://example.com/dirs/d1/files",
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
  "xreginstance": "B9282-129301",

  "data": {
    "action": "io.xregistry.registry.updated",
    "registry": "https://example.com",
    "xid": "/",
    "time": "2025-07-02T12:00:01Z",
    "instance": "B9282-129301",
    "epoch": 2,
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
  "xreginstance": "B9282-129301",
  "data": {
    "action": "io.xregistry.group.created",
    "registry": "https://example.com",
    "xid": "/dirs/d1",
    "time": "2025-07-02T12:00:01Z",
    "instance": "B9282-129301",
    "epoch": 1
  }
}
```
