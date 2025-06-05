#!/bin/bash

# Script to import all xRegistry files to https://xregistry.soaphub.org
# Usage: ./import_all.sh

echo "Starting import of all xRegistry files..."
echo "Target registry: https://xregistry.soaphub.org"
echo ""

# Counter for tracking imports
success_count=0
fail_count=0

# Loop through all .xreg.json files in the current directory
for file in *.xreg.json; do
    if [ -f "$file" ]; then
        echo "Importing: $file"

        # Run the xr import command
        if xr import -s https://xregistry.soaphub.org -v -d@"$file"; then
            echo "✓ Successfully imported: $file"
            ((success_count++))
        else
            echo "✗ Failed to import: $file"
            ((fail_count++))
        fi
        echo ""
    fi
done

# Summary
echo "Import completed!"
echo "Successfully imported: $success_count files"
echo "Failed imports: $fail_count files"

if [ $fail_count -eq 0 ]; then
    echo "All files imported successfully! 🎉"
    exit 0
else
    echo "Some imports failed. Please check the output above."
    exit 1
fi
