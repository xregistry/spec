# Schema Samples

This directory contains schema-centric sample material for the CloudEvents
Registry model.

## Files

- [schemastore_org.xreg.json](schemastore_org.xreg.json): generated xRegistry
  document that indexes JSON Schema definitions published by SchemaStore.
- [schemastore_org.py](schemastore_org.py): helper script that clones the
  SchemaStore repository, detects each schema draft version, and emits
  `schemastore_org.xreg.json`.

## Regenerating The SchemaStore Sample

From this directory:

```bash
python schemastore_org.py
```

The script requires `git` and Python 3 and overwrites
[schemastore_org.xreg.json](schemastore_org.xreg.json).
