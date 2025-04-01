#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script clones the SchemaStore repository from GitHub into a temporary directory,
scans the "src/schemas/json" folder for all *.json files, opens each file to detect its
JSON Schema draft version (by inspecting the "$schema" property), groups the files by base name
(removing any trailing "-<version>"), and produces an xRegistry JSON document with external
references to the raw GitHub URLs.

Each registry version entry contains:
  - schemauri: Constructed from the raw GitHub URL plus the filename.
  - description: A generic description based on the filename.
  - format: "JSONSchema/Draft/<detected draft>", reflecting the JSON Schema draft version
            with "Draft" capitalized.

The temporary clone is automatically cleaned up when the script finishes.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict

# Base URI for raw GitHub access to schema files.
BASE_URI = "https://raw.githubusercontent.com/SchemaStore/schemastore/master/src/schemas/json/"

# Regular expression to detect filenames ending with a version suffix (e.g. "name-1.0.0").
VERSION_PATTERN = re.compile(r"^(.*)-(\d+(?:\.\d+)*(?:[xX])?)$")

def get_schema_draft(file_path):
    """
    Opens a JSON file and extracts the JSON Schema draft version from its "$schema" property.
    
    Args:
        file_path (str): Path to the JSON file.
    
    Returns:
        str: Detected JSON Schema draft version (e.g., "draft-07") or "unknown" if not found.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        schema_url = data.get("$schema", "")
        if "draft-04" in schema_url:
            return "draft-04"
        elif "draft-06" in schema_url:
            return "draft-06"
        elif "draft-07" in schema_url:
            return "draft-07"
        elif "draft/2019-09" in schema_url:
            return "draft/2019-09"
        elif "draft/2020-12" in schema_url:
            return "draft/2020-12"
        else:
            return "unknown" if not schema_url else schema_url
    except Exception as e:
        return f"error: {e}"

def group_files_by_base(directory):
    """
    Recursively scans the given directory for *.json files, determines the base name
    (by removing any trailing "-<version>"), extracts the version (or uses "1.0.0" as default),
    and detects the JSON Schema draft version.
    
    Args:
        directory (str): The directory to scan.
    
    Returns:
        dict: Mapping from base name to a dictionary mapping version strings to a dict with:
              - "filename": the filename (with extension)
              - "draft": the detected JSON Schema draft version.
    """
    groups = defaultdict(dict)
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".json"):
                full_path = os.path.join(root, file)
                base_name, _ = os.path.splitext(file)
                match = VERSION_PATTERN.match(base_name)
                if match:
                    base = match.group(1)
                    version = match.group(2)
                else:
                    base = base_name
                    version = "1.0.0"
                draft = get_schema_draft(full_path)
                groups[base][version] = {
                    "filename": file,
                    "draft": draft
                }
    return groups

def build_registry(groups):
    """
    Constructs the registry document from the grouped file information.
    
    Each version entry includes the "format" field set to "JSONSchema/Draft/<detected draft>".
    
    Args:
        groups (dict): Grouped filenames with version and draft info.
    
    Returns:
        dict: The complete registry document.
    """
    registry = {
        "$schema": "https://cloudevents.io/schemas/registry",
        "specversion": "1.0-rc1",
        "schemagroups": {
            "schemastore_org.json": {
                "schemas": {}
            }
        }
    }
    schemas = registry["schemagroups"]["schemastore_org.json"]["schemas"]
    for base, versions in groups.items():
        version_entries = {}
        for ver, info in sorted(versions.items()):
            # Capitalize the draft string (e.g. "draft-07" -> "Draft-07")
            draft_cap = info["draft"].capitalize() if info["draft"] else "unknown"
            version_entries[ver] = {
                "schemauri": BASE_URI + info["filename"],
                "description": f"Schema for {info['filename']}",
                "format": f"JSONSchema/{draft_cap}"
            }
        schemas[base] = {
            "versions": version_entries
        }
    return registry

def clone_schemastore_repo():
    """
    Clones the SchemaStore repository into a temporary directory.
    
    Returns:
        tuple: (TemporaryDirectory object, path to the "src/schemas/json" directory)
    """
    temp_dir = tempfile.TemporaryDirectory()
    clone_dir = os.path.join(temp_dir.name, "schemastore")
    try:
        subprocess.check_call(["git", "clone", "https://github.com/SchemaStore/schemastore.git", clone_dir])
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error cloning repository: {e}\n")
        temp_dir.cleanup()
        sys.exit(1)
    schemas_dir = os.path.join(clone_dir, "src", "schemas", "json")
    if not os.path.isdir(schemas_dir):
        sys.stderr.write(f"Directory not found: {schemas_dir}\n")
        temp_dir.cleanup()
        sys.exit(1)
    return temp_dir, schemas_dir

def main():
    """
    Main function that clones the SchemaStore repository into a temporary directory,
    scans the "src/schemas/json" folder for *.json files, builds the registry document
    (setting the "format" field based on the detected draft version with "Draft" capitalized),
    and writes the registry to 'registry.json'.
    """
    temp_dir_obj, schemas_dir = clone_schemastore_repo()
    groups = group_files_by_base(schemas_dir)
    registry = build_registry(groups)
    with open("schemastore_org.xreg.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print("Registry generated and saved to 'schemastore_org.xreg.json'.")
    # Cleanup the temporary directory
    temp_dir_obj.cleanup()

if __name__ == "__main__":
    main()
