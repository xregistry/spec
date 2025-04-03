# Samples

<!-- no verify-specs -->

This directory contains some sample xRegistry models and data that can be
used to either jump-start your usage/deployment of an xRegistry instance or
to help with learning about xRegistry.

There are more samples in the [cloudevents](../../cloudevents/samples)
directory that cover the messaging and eventing domains.

## Document Store

A simple document store registry. Each "file" (resource) lives within a
"directory" (group) and can be versioned. This is akin to a filesystem and
makes no statement as to the types of files stored. Client can use the
`contenttype` (Content-Type HTTP header) to determine the type of each file.

Each type/format of file would need to have its own (unique) id within
the owning directory.

Model:
- Group: `dirs` / `dir`
  - Resources: `files` / `file`

Files:
- Model: [doc-store-model.json](doc-store-model.json)
- Data: [doc-store-data.json](doc-store-data.json)

## Multi-Format Document Store

This example is another document store, however, in this case the format of
the documents stored needs to be a first class concept in the model. So, in
this case the "document" maps to the xRegistry "group" and the document
"format" maps to the xRegistry "resource".

In this model each document does not need to have a unique id for each format,
rather in this scenario the document id (and often "name") will be the same for
all formats. Thus the XID for a single document and format would look something
like: `docs/form-1040/formats/pdf` and `docs/form-1040/formats/ms-word`.
Each format of the documents can then be versioned as needed.

Model:
- Group: `docs` / `doc`
  - Resources: `formats` / `format`

Files:
- Model: [formatted-doc-store-model.json](formatted-doc-store-model.json)
- Data: [formatted-doc-store-data.json](formatted-doc-store-data.json)

