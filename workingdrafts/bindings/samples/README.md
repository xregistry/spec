# Document-Tree Binding Example

<!-- words: gitattributes py walkthrough workingdrafts -->

The [mapping directory](mapping) contains the complete example
for the [directory mapping format](../mapping.md). The
[Git](../git.md) and [File](../file.md) bindings select that directory
without changing its metadata or document bytes.

For a smaller starting point, [mapping-example](mapping-example) contains
the walkthrough from the specification: one existing document and a single
`registry.json` that embeds every record and index inline. The walkthrough
shows that file with its expected read results, and a variant that keeps one
collection in a separate file. Start there when authoring a mapping by hand.

[registry.json](mapping/registry.json) is the entry point. This sample uses the
split form, so its references lead to separate collection index files, entity
record files and exact document bytes. It includes
explicit default Versions, local aliases, metadata-only Resources, a binary
document and an empty document.

Run from the repository root:

```text
python -B -m workingdrafts.bindings.tools.mapping_examples validate workingdrafts\bindings\samples\mapping
```

The `build-sample` operation with `--inline` writes the same Registry with
all metadata embedded in one `registry.json`.

The physical filenames in this generated example are storage allocations,
not xRegistry IDs or mandatory directory names. Existing projects can instead
add `registry.json` and metadata alongside their own files. The
[directory mapping tests](../tools/test_directory_mapping.py) read an
existing project layout with File and Git. Neither binding moves or modifies
its content.

The sample's `.gitattributes` preserves JSON line endings and prevents text
conversion of document content. It is not part of the snapshot's containment
graph.
