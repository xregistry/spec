# Resource Update Samples

<!-- words: fileid valign cellborder cellpadding -->

This document shows a set of write operations that provide concrete examples of
how the [Resource Processing Algorithm](./spec.md#resource-processing-algorithm)
is applied based on the state of the Registry and the incoming request.  They
are meant to be read in order to avoid repeating the same commentary for each
example.

## Table of Contents

- [The Setup](#the-setup)
- [Create single Resource with empty content](#create-single-resource-with-empty-content)
- [Create Resource via the "files" collection](#create-resource-via-the-files-collection)
- [Create Resource with some Versions, no defaultversionid](#create-resource-with-some-versions-no-defaultversionid)
- [Create Resource with Versions and defaultversionid](#create-resource-with-versions-and-defaultversionid)
- [Create Resource with defaultversionid](#create-resource-with-defaultversionid)
- [Create Resource with versionid and Versions](#create-resource-with-versionid-and-versions)
- [Update Resource with new Versions and ne sticky default Version](#update-resource-with-new-versions-and-ne-sticky-default-version)
- [Create Resource with Versions and sticky default Version](#create-resource-with-versions-and-sticky-default-version)
- [Create Resource with versionid and defaultversionid](#create-resource-with-versionid-and-defaultversionid)
- [Create Resource with sticky defaultversionid](#create-resource-with-sticky-defaultversionid)
- [Update Resource with non-sticky bad defaultversionid](#update-resource-with-non-sticky-bad-defaultversionid)
- [Update Resource with sticky non-specified defaultversionid](#update-resource-with-sticky-non-specified-defaultversionid)
- [Patch Resource with Versions and defaultversionsticky](#patch-resource-with-versions-and-defaultversionsticky)
- [Update Resource with empty content](#update-resource-with-empty-content)
- [Patch new Resource with empty content](#patch-new-resource-with-empty-content)
- [Update Resource with new description](#update-resource-with-new-description)
- [Patch Resource's description field](#patch-resources-description-field)
- [Update Resource with non-specified defaultversionsticky](#update-resource-with-non-specified-defaultversionsticky)
- [Patch Resource with defaultversionsticky](#patch-resource-with-defaultversionsticky)
- [Patch Resource with sticky defaultversionid](#patch-resource-with-sticky-defaultversionid)
- [Patch Resource with bad defaultversionid](#patch-resource-with-bad-defaultversionid)
- [Update Resource with bad sticky defaultversionid](#update-resource-with-bad-sticky-defaultversionid)
- [Update Resource with non-specified sticky default Version](#update-resource-with-non-specified-sticky-default-version)
- [Create Resource with conflicting default Version attributes - variant 1](#create-resource-with-conflicting-default-version-attributes---variant-1)
- [Create Resource with conflicting default Version attributes - variant 2](#create-resource-with-conflicting-default-version-attributes---variant-2)
- [Create Resource with conflicting default Version attributes - variant 3](#create-resource-with-conflicting-default-version-attributes---variant-3)


### The Setup

Each example:
- Only includes the key attributes that are important from an "understanding"
  perspective.
- Includes explanatory text, highlighting the key aspects.
- Timestamps will only use a year or "now" (meaning it was updated to the
  current time) rather than a full RFC3330 timestamp to make it easier to
  detect changes in values.
- Has a model defined as:

```
        {
          "groups": {
            "dirs": {
              "singular": "dir",
              "resources": {
                "files": {
                  "singular": "file",
                  "hasdocument": false,
                  "versionmode": "createdat"
                }
              }
            }
          }
        }
```

### Create single Resource with empty content

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- A new Resource `f1` is created.
- A Version with a `versionid` of `1` is created per the default `versionid`
  naming algorithm defined in the specification. </li>
- Conceptually, this new Version is populated with the Resource's default
  Version attributes from the request. However, since there are none, all
  mandatory attributes are assigned their default values.
- The Version's `ancestor` value is `1` (points to itself) because it is the
  root of a hierarchy tree.
- Being the only Version, it is the default Version, and it is not "sticky".
- Using `PATCH` instead of `PUT` will yield the exact same results.

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource via the "files" collection

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
POST /dirs/d1/files

{
  "f1": {
    "name": "my file"
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "f1": {
    "fileid": "f1",
    "versionid": "1",
    "epoch": 1,
    "name": "my file",
    "isdefault": true,
    "createdat": "now",
    "modifiedat": "now",
    "ancestor": "1",

    "meta": {
      "epoch": 1,
      "createdat": "now",
      "modifiedat": "now",
      "defaultversionid": "1",
      "defaultversionsticky": false
    },
    "versions": {
      "1": { see Resource.* attrs }
    }
  }
}
```

</td></tr></table>

**Notes:**

- Similar to previous example, but creating the Resource via the owning
  Group's `files` collection.
- The default Version properties include `name`, so that will appear both at
  the Resource level and within the Version in the `versions` collection.

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource with some Versions, no defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "versions": {
    "v1": {},
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "1": {
      "epoch": 1,
      "name": "foo",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "1"
    },
    "v1": {
      "epoch": 1,
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- After creating the Resource, `f1`, Versions `v1` and `v2` are created.
- Then, Version `1` is created from the Resource's default Version attributes
  (including `name`) due to no indication as to what its `versionid` is -
  meaning, no `versionid` or `meta.defaultversionid` being present - so a new
  Version with the next server-generated `versionid` value (`1`) being used.
- Since all Versions have the same `createdat` timestamp they are sorted
  alphabetically by their `versionid` values in order to set their `ancestor`
  attributes.
- Which means `v2` becomes the newest and therefore the default Version.
- Ancestor order: `1` <- `v1` <- `v2`.
- Using `PATCH` would yield the exact same results.

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource with Versions and defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionid": "v1"
  },
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {
      "createdat": "3030"
    },
    "v3": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "3030",
  "modifiedat": "now",
  "ancestor": "v3",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "epoch": 1,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs },
    "v3": {
      "epoch": 1,
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    }
  }
}
```

</td></tr></table>

**Notes:**

- No version `1` is created because we used `meta.defaultversionid` as a clue
  that Resource.* attributes are for `v1`.
- Resource.* attributes (eg `name`) is ignored because `v1` is part of the
  request's `versions` collection.
- Ancestor order: `v1`(2020) <- `v3` (now) <- `v2` (3030).
- Version `v2` is default because it has the newest `createdat` timestamp.

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource with defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionid": "v1"
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "name": "foo",
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Version `v1` is created due to `meta.defaultversionid` being set.
- Since `v1` isn't part of the request's `versions` collection, the Resource.*
  attributes will be applied.

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource with versionid and Versions

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "versionid": "v0",
  "name": "foo",
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v0",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v0": {
      "epoch": 1,
      "name": "foo"
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v1": {
      "epoch": 1,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Version `v0` is created because it is not present in `versions`.
- Ancestor order: `v1` (2020) <- `v0` (now) <- `v2` (now).

<hr>

<!-- ----------------------------------------------------------------- -->

### Update Resource with new Versions and ne sticky default Version

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v0",
  "epoch": 1
  "isdefault": true,
  "createdat": "2021",
  "modifiedat": "2021",
  "ancestor": "v0",

  "meta": {
    "epoch": 1,
    "createdat": "2021",
    "modifiedat": "2021",
    "defaultversionid": "v0",
    "defaultversionsticky": false
  },

  "versions": {
    "v0": { see Resource.* attrs }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2020",
  "modifiedat": "now",
  "ancestor": "v0",

  "meta": {
    "epoch": 2,
    "createdat": "2021",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v0": {
      "epoch": 2,
      "name": "foo",
      "createdat": "2021",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v1": {
      "epoch": 1,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Version `v0` (the current default Version) is updated with the
  Resource.* attributes. Notice that `versionid` is not present in the request
  and that it isn't needed as a "clue" because the Resource already exists
  so we know what the current default Version is.
- While `meta.defaultversionid` is not used as a clue as to the "current"
  default `versionid`, it will be used to calculate the resulting default
  Version due to `defaultversionsticky` being `true`.
- Ancestor order: `v1` (2020) <- `v0` (2021) <- `v2` (now).

<hr>

<!-- ----------------------------------------------------------------- -->

### Create Resource with Versions and sticky default Version

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "versionid": "v0",
  "name": "foo",
  "meta": {
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2020",
  "modifiedat": "now",
  "ancestor": "v0",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v0": {
      "epoch": 1,
      "name": "foo",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v1": {
      "epoch": 1,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- In this case `versionid` at the Resource level is needed to ensure that
  the current default Version is `v0` and that it is created.
- Notice that the 2 potential "clues" (`versionid` and `meta.defaultversionid`)
  have different values because we need to create `v0` as the current default
  Version when processing the Resource.* attributes, but then assign `v1` as
  the resulting default Version. This means that in the previous example
  `versionid` was not needed, but in this example it is to yield the correct
  (same) net result.
- Ancestor order: `v1` (2020) <- `v0` (now) <- `v2` (now).

<hr>

<!--  ----------------------------------------------------------------- -->

### Create Resource with versionid and defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "versionid": "v0",
  "name": "foo",
  "meta": {
    "defaultversionid": "v1"
  },
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v0",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v0": {
      "epoch": 1,
      "name": "foo",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v1": {
      "epoch": 1,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Version `v0` is created due to the presence of `versionid`. Which means
  `meta.defaultversionid` is ignored for the purpose of determining the
  current default Version. However, it is also ignored when calculating the
  resulting default Version due to `defaultversionsticky` being `false`.
- Ancestor order: `v1` (2020) <- `v0` (now) <- `v2` (now).

<hr>

<!--  ----------------------------------------------------------------- -->

### Create Resource with sticky defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "meta": {
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {
      "createdat": "2020"
    },
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2020",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
      "epoch": 1,
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    }
  }
}
```

</td></tr></table>

**Notes:**

- In this case since `versionid` is not present, `meta.defaultversionid` will
  be used as the "clue" for the current default Version.
- And, Version v1 will be the default and it's sticky.

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with non-sticky bad defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
      "createdat": "2025",
      "ancestor": "v1"
    }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionid": "abc"
  },
  "versions": {
    "v2": {
      "createdat": "2020"
    }
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 2,
  "name": "foo",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "v2",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
      "epoch": 2,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v2"
    }
  }
}
```

</td></tr></table>

**Notes:**

- Current default Version is `v1`, and `v1` is not in the request's `versions`
  collection, so it's "name" attribute is updated.
- Version `v2` is updated.
- While `meta.defaultversionid` references a non-existing Version, no error is
  generated because its value is ignored due to `meta.defaultversionsticky`
  being `false`.
- Ancestor order: `v2` (2020) <- `v1` (2025).

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with sticky non-specified defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "epoch": 1,
      "createdat": "2025",
      "modifiedat": "2025",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
    }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionsticky": true
  },
  "versions": {
    "v2": {
      "createdat": "2020"
    }
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "v2",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
      "epoch": 2,
      "createdat": "2020",
      "modifiedat": "now",
      "ancestor": "v2"
    }
  }
}
```

</td></tr></table>

**Notes:**

- Notice that "Resource.name" is ignored because `v2` (the current default
  Version) appears in the request's `versions` collection.
- While the current default is `v2`, setting `defaultversionsticky` to `true`
  only takes effect after the default Version is recalculated. This is due to
  the fact that `PUT` is a complete replacement and `meta.defaultversionid`
  not being in the request is akin to setting it to `null` in the request. In
  the next example we'll see how `PATCH` changes this semantics.
- Ancestor order: `v2` (2020) <- `v1` (2025).

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch Resource with Versions and defaultversionsticky

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "epoch": 1,
      "createdat": "2025",
      "modifiedat": "2025",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
    }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1

{
  "name": "foo",
  "meta": {
    "defaultversionsticky": true
  },
  "versions": {
    "v2": {
      "createdat": "2020"
    }
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2020",
  "modifiedat": "now",
  "ancestor": "v2",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {
      "epoch": 2,
      "createdat": "2025",
      "modifiedat": "now",
      "ancestor": "v2"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Resource.name is ignored due to `v2` (the current default Version) being in
  the request's `versions` collection.
- Since this is a `PATCH`, unlike the previous example where
  `meta.defaultversionid` was implicitly set to `null`, in this case its value
  remains unchanged. So, when `meta.defaultversionsticky` is set to `true` the
  current default Version becomes "sticky".
- Ancestor order: `v2` (2020) <- `v1` (2025).

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with empty content

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Notice that `name` is deleted because `PUT` is a complete replacement
  of all attributes.
- No attributes in `meta` are updated.

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch new Resource with empty content

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },

  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1

{}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Notice this time `name` is unchanged due to the use of `PATCH` instead of
  `PUT`.
- However, `PATCH` does update the `epoch` and `modifiedat` timestamps of the
  current default Version.
- The `meta` sub-object is unchanged.

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with new description

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "description": "very cool"
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "isdefault": true,
  "description": "very cool",
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Default Version's `name` attribute is deleted.
- Its `description` is updated.
- Its `epoch` and `modifiedat` are automatically updated.
- The `meta` sub-object is unchanged.

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch Resource's description field

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1

{
  "description": "very cool"
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "name": "my file",
  "isdefault": true,
  "description": "very cool",
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Default Version's `name` attribute is unchanged.
- Its `description` is updated.
- Its `epoch` and `modifiedat` are automatically updated.
- The `meta` sub-object is unchanged.

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with non-specified defaultversionsticky

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "meta: {
    "defaultversionsticky": true
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "1",
    "defaultversionsticky": true
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- The default Version's `name` attribute is deleted due to the operation
  being a `PUT`. Its `epoch` and `modifiedat` are automatically updated.
- `meta.defaultversionsticky` is set to `true`, and since there is only one
  Version the calculated default Version remains `1`.

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch Resource with defaultversionsticky

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1

{
  "meta: {
    "defaultversionsticky": true
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 2,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "now",
  "ancestor": "1",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "1",
    "defaultversionsticky": true
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- `name` is unchanged, but `epoch` and `modifiedat` are automatically updated.
- As with previous example, Version `1` becomes sticky.
- The default Version's `name` attribute is unchanged, but `epoch` and
  `modifiedat` are automatically updated.
- `meta.defaultversionsticky` is set to `true`, and since there is only one
  Version the calculated default Version remains `1`.

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch Resource with sticky defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "epoch": 1,
      "createdat": "2025",
      "modifiedat": "2025",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1/meta

{
  "defaultversionid": "v1",
  "defaultversionsticky": true
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
      "epoch": 1,
      "createdat": "2025",
      "modifiedat": "2025",
      "ancestor": "v1"
    }
  }
}
```

</td></tr></table>

**Notes:**

- Notice the operation is directed to the `meta` sub-object, no attributes
  on Version `v1` or `v2` are modified.
- However, per the request, the default Version is set to `v1` and it is
  sticky.
- The `meta`'s `epoch` and `modifiedat` values are updated.
- Ancestor order: `v1` (2025) <- `v2` (2025).

<hr>

<!--  ----------------------------------------------------------------- -->

### Patch Resource with bad defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PATCH /dirs/d1/files/f1

{
  "meta: {
    "defaultversionid": "foo"
  }
}
```

</td><td valign=top>

**Response:**

```
Error due to `foo` being an unknown Version.
```

</td></tr></table>

**Notes:**

- While the request didn't set `meta.defaultversionsticky` to `true`
  explicitly, setting `meta.defaultversionid` via a `PATCH` implicitly
  sets `meta.defaultversionsticky` to `true`. If this operation used `PUT`
  instead, the error would not have been generated and `meta.defaultversionid`
  would have been ignored.

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with bad sticky defaultversionid

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "1",
  "epoch": 1,
  "name": "my file",
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "1",
    "defaultversionsticky": false
  },
  "versions": {
    "1": { see Resource.* attrs }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "meta: {
    "defaultversionid": "foo",
    "defaultversionsticky": true
  }
}
```

</td><td valign=top>

**Response:**

```
Error due to `foo` being an unknown Version.
```

</td></tr></table>

**Notes:**

- Similar to the previous example, except using `PUT`. If
  `meta.defaultversionsticky` had not been included in the request with a
  value of `true` then `defaultversionid` would have been ignored.

<hr>

<!--  ----------------------------------------------------------------- -->

### Update Resource with non-specified sticky default Version

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 1,
  "isdefault": true,
  "createdat": "2025",
  "modifiedat": "2025",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "2025",
    "modifiedat": "2025",
    "defaultversionid": "v1",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": { ... }
  }
}
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "name": "foo",
  "createdat": "1999"
  "meta": {
    "defaultversionsticky": true
  },
  "versions": {
     "v2": { "createdat": "1998" }
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v1",
  "epoch": 2,
  "name": "foo",
  "isdefault": true,
  "createdat": "1999",
  "modifiedat": "now",
  "ancestor": "v2",

  "meta": {
    "epoch": 2,
    "createdat": "2025",
    "modifiedat": "now",
    "defaultversionid": "v1",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": { see Resource.* attrs },
    "v2": {
       "epoch": 1,
       "createdat": "1998",
       "modifiedat": "now",
       "ancestor": "v2"
     }
  }
}
```

</td></tr></table>

**Notes:**

- Version `v2` is created with a `createdat` value of `1998`.
- Version `v1` is updated (`name`, `createdat`, `epoch` and `modifiedat`).
- While `v2` was just created, `v1` is still the default Version because it has
  a newer `createdat` value. And it is now sticky per the request.
- Ancestor order: `v2` (1998) <- `v1` (1999).

<hr>

<!--  ----------------------------------------------------------------- -->

### Create Resource with conflicting default Version attributes - variant 1

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "versionid": "v1",
  "name": "foo",
  "meta": {
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {"name":"abc"},
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": true
  },
  "versions": {
    "v1": {
      "name": "abc",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Resource.name is ignored because `v1` is in request's `versions` collection.
- Version `v2` is default because it's the highest alphabetically.

<hr>

<!--  ----------------------------------------------------------------- -->

### Create Resource with conflicting default Version attributes - variant 2

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "meta": {
    "defaultversionid": "v1"
  },
  "versions": {
    "v1": {"name":"abc"},
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "name": "abc",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Resource.* attributes (implied "null" values because they're missing) are
  ignored because `v1` is in the request's `versions` collection.
- Version `v2` is default because it's the highest alphabetically,
- Despite `meta.defaultversionid` being specified, it is ignored when
  calculating the default Version because `meta.defaultversionsticky` is not
  `true`.

<hr>

<!--  ----------------------------------------------------------------- -->

### Create Resource with conflicting default Version attributes - variant 3

<table border=1 cellpadding=5 cellborder=1><tr><td valign=top>

**Initial State:**

```
Empty
```

**Request:**

```
PUT /dirs/d1/files/f1

{
  "versionid": "v1",
  "versions": {
    "v1": {"name":"abc"},
    "v2": {}
  }
}
```

</td><td valign=top>

**Response:**

```
{
  "fileid": "f1",
  "versionid": "v2",
  "epoch": 1,
  "isdefault": true,
  "createdat": "now",
  "modifiedat": "now",
  "ancestor": "v1",

  "meta": {
    "epoch": 1,
    "createdat": "now",
    "modifiedat": "now",
    "defaultversionid": "v2",
    "defaultversionsticky": false
  },
  "versions": {
    "v1": {
      "name": "abc",
      "createdat": "now",
      "modifiedat": "now",
      "ancestor": "v1"
    },
    "v2": { see Resource.* attrs }
  }
}
```

</td></tr></table>

**Notes:**

- Same net results as previous example.
