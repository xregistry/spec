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
[CloudEvent](https://cloudevents.io) context attributes. Whether CloudEvents
are used in the generation/serialization of the events is OPTIONAL, but it is
RECOMMENDED.

This specification does not mandate the mechanisms by which events are sent
to consumers, nor does it mandate how consumers register interest in receiving
events.

Below is a sample event serialized as a "structured" JSON CloudEvent due to a
Group's `name` being modified:

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
within the scope of one interaction (see
[`xregcorrelationid`](#xregcorrelationid-extension-context-attribute)), the
following constraints apply:
- Only one `created`, `updated` or `deleted` event MUST be generated per
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
  - `deprecated`
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

The time when the interaction occurred. This value MUST be the same for
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
  "epoch": UINTEGER, ?
  "meta.epoch": UINTEGER, ?
  "changed": [ "<STRING>", * ] ?
}
```

where:
- The `epoch` attribute MUST be included in `created` and `updated` events
  for Registries, Groups, Resources and Versions; and it MUST be the `subject`
  entity's `epoch` value as seen at the end of the interaction.

  - MUST NOT be included in `deleted` events.

- The `meta.epoch` attribute MUST be included in Resource `created` and
  `updated` events and it MUST be the `subject` Resource's `meta.epoch` value
  as seen at the end of the interaction.

  - MUST only be included for Resource related events.

  - MUST NOT be included in Resource `deleted` events.

  - Note that Resource `created` and `updated` events will include both
    `epoch` and `meta.epoch` attributes even if one of them didn't change for
    the interaction.

- The `changed` attribute MAY be included to indicate which attributes of the
  `subject` entity were modified. When present, has the following
  constraints:

  - MUST be a list of the top-level attribute names (not values) that were
    added, modified, or deleted for the `subject` entity.

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

Implementations MAY define their own metadata to be included in the `data` of
a CloudEvent.

This metadata (`data`) is NOT REQUIRED to be present in the event, but is
RECOMMENDED.

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
      that a `io.xregistry.version.update` event MUST also be generated.

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
      a `io.xregistry.deprecated` event is also generated. And in that
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

In these examples, unless otherwise stated, assume that the Registry has
the base URL `https://example.com` and the following model definition. The
Resources are metadata-only, so metadata PATCH requests use unsuffixed URLs.

```yaml
{
  "groups": {
    "dirs": {
      "singular": "dir",
      "resources": {
        "files": {
          "singular": "file",
          "hasdocument": false
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
    - `subject`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Create a tree of entities

- Empty Registry
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v1`
  - Body: `{}`
- Events:
  - `io.xregistry.registry.updated`
    - `subject`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `dirs`, `dirscount`
  - `io.xregistry.group.created`
    - `subject`: `/dirs/d1`
    - `epoch`: Group's `epoch` value
  - `io.xregistry.resource.created`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value
    - `meta.epoch`: Resource's `meta.epoch` value
  - `io.xregistry.version.created`
    - `subject`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value

### Update a Resource attribute (a default Version attribute)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, default `v1`'s `epoch`)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - `subject`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Update a Resource's meta sub-object

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibility": "backward" }`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `meta.compatibility`

### Update a Resource's meta sub-object and deprecate the Resource

- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "compatibility": "backward", "deprecated": {...} }`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `meta.compatibility`,
      `meta.deprecated`
  - `io.xregistry.resource.deprecated`
    - `subject`: `/dirs/d1/files/f1`

### Import an entire Registry

- Empty Registry
- Interaction:
  - `PUT /`
  - Body: Registry attributes, `modelsource`, `capabilities`, Groups,
    Resources, Versions
- Events:
  - `io.xregistry.registry.updated`
    - `subject`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `model`, `modelsource`, `capabilities`,
      `<GROUPS>`, `<GROUPS>count`, `<OTHER-REGISTRY-ENTITY-ATTRIBUTES>`
  - `io.xregistry.model.updated`
    - `subject`: `/model`
  - `io.xregistry.modelsource.updated`
    - `subject`: `/modelsource`
  - `io.xregistry.capabilities.updated`
    - `subject`: `/capabilities`
  - `io.xregistry.group.created` for each new Group
    - `subject`: `/dirs/d1`
    - `epoch`: Group's `epoch` value
  - `io.xregistry.resource.created` for each new Resource
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
  - `io.xregistry.version.created` for each new Version
    - `epoch`: Version's `epoch` value
    - `subject`: `/dirs/d1/files/f1/versions/v1`

### Create a new Version - non-sticky

- Current default Version (v1) is not "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
      `versions`, `versionscount`,
      `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - `epoch`: Version's `epoch` value
    - `subject`: `/dirs/d1/files/f1/versions/v2`

### Create a new Version - sticky

- Current default Version (v1) is "sticky"
- Interaction:
  - `PUT /dirs/d1/files/f1/versions/v2`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - `epoch`: Version's `epoch` value
    - `subject`: `/dirs/d1/files/f1/versions/v2`

### Change `defaultversionid` pointer

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/meta`
  - Body: `{ "defaultversionid": "v2" }`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`

  Note that no `io.xregistry.version.updated` event is generated.

### Update a Version attribute (the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v1`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`
  - `io.xregistry.version.updated`
    - `subject`: `/dirs/d1/files/f1/versions/v1`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Update a Version attribute (not the default Version)

- Current default Version is `v1`
- Interaction:
  - `PATCH /dirs/d1/files/f1/versions/v2`
  - Body: `{ "name": "foo" }`
- Events:
  - `io.xregistry.version.updated`
    - `subject`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value
    - `changed`: `epoch`, `modifiedat`, `name`

### Create a new Version - not sticky

- Current default Version (v1) is not "sticky"
- Interaction:
  - `POST /dirs/d1/files/f1`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.defaultversionid`, `meta.epoch`, `meta.modifiedat`,
       `versions`, `versionscount`,
       `<ALL-OLD-AND-NEW-DEFAULT-VERSION-ATTRIBUTES>`,
  - `io.xregistry.version.created`
    - `subject`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Create a new Version - sticky

- Current default Version (v1) is "sticky"
- Interaction:
  - `POST /dirs/d1/files/f1`
  - Body: `{}`
- Events:
  - `io.xregistry.resource.updated`
    - `subject`: `/dirs/d1/files/f1`
    - `epoch`: Resource's `epoch` value (technically, the default Version's)
    - `meta.epoch`: Resource's `meta.epoch` value
    - `changed`: `meta.epoch`, `meta.modifiedat`, `versions`, `versionscount`
  - `io.xregistry.version.created`
    - `subject`: `/dirs/d1/files/f1/versions/v2`
    - `epoch`: Version's `epoch` value

### Delete a Group

- Interaction:
  - `DELETE /dirs/d1`
- Events:
  - `io.xregistry.registry.updated`
    - `subject`: `/`
    - `epoch`: Registry's `epoch` value
    - `changed`: `dirs`, `dirscount`, `epoch`, `modifiedat`
  - `io.xregistry.group.deleted`
    - `subject`: `/dirs/d1`
  - `io.xregistry.resource.deleted` for each deleted Resource
    - `subject`: `/dirs/d1/files/f1`
  - `io.xregistry.version.deleted` for each deleted Version
    - `subject`: `/dirs/d1/files/f1/versions/v1`

### Creating a Group with a complete client HTTP message exchange

Assume Group `d1` does not exist and the Registry's `epoch` is 1.

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
xRegistry-xregcorrelationid: B9282-129301

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
  "xregcorrelationid": "B9282-129301",
  "data": {
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
  "xregcorrelationid": "B9282-129301",
  "data": {
    "epoch": 1
  }
}
```
