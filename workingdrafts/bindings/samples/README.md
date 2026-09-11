# Document-Tree Binding Example

<!-- words: gitattributes py walkthrough workingdrafts -->

The [mapping directory](mapping) contains the complete example
for the [directory mapping format](../mapping.md). The
[Git](../git.md) and [File](../file.md) bindings select that directory
without changing its metadata or document bytes.

For a smaller starting point, [mapping-example](mapping-example) contains
the nine files used by the complete walkthrough in the specification.
Every JSON file is shown in that walkthrough, together with the expected
read results. Start there when authoring a mapping by hand.

[registry.json](mapping/registry.json) is the entry point. Its references lead to
the collection indexes, entity records and exact document bytes. It includes
explicit default Versions, local aliases, metadata-only Resources, a binary
document and an empty document.

```text
python -B tools\mapping_examples.py validate workingdrafts\bindings\samples\mapping
```

The physical filenames in this generated example are storage allocations,
not xRegistry IDs or mandatory directory names. Existing projects can instead
add `registry.json` and metadata alongside their own files. See
[the directory mapping tests](../../../tools/test_directory_mapping.py) for
an existing project layout read through both File and Git without moving or
modifying its content.

The sample's `.gitattributes` preserves JSON line endings and prevents text
conversion of document content. It is not part of the snapshot's containment
graph.
