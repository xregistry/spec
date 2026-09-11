# Document-Tree Binding Example

<!-- words: gitattributes py workingdrafts -->

The [document-tree directory](document-tree) contains the complete example
for the [shared document-tree format](../document-format.md). The
[Git](../git.md) and [File](../file.md) bindings select that directory
without changing its metadata or document bytes.

[registry.json](document-tree/registry.json) is the entry point. Its references lead to
the collection indexes, entity records and exact document bytes. It includes
explicit default Versions, local aliases, metadata-only Resources, a binary
document and an empty document.

```text
python -B tools\document_examples.py validate workingdrafts\bindings\samples\document-tree
```

The physical filenames are storage allocations, not xRegistry IDs. The
sample's `.gitattributes` preserves JSON line endings and prevents text
conversion of document content. It is not part of the snapshot's containment
graph.
